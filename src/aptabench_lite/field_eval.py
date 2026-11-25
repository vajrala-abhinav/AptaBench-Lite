"""Small, optional Pool and Kd evaluators.

These never call/alter sequence alignment, sequence assignment, or its denominators.
Kd is one annotated measurement per gold aptamer. Pool is a distinct library
template/type per paper, not a repeated success for every aptamer in that pool.
Ambiguous identity is exposed to review instead of selected by numerical proximity.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re

from .models import base_run
from .normalization import name_key
from .readers import rows, parse_items, alias, raw_json

NUM = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
UNIT_SCALE = {
    "fm": Decimal("0.000001"), "pm": Decimal("0.001"),
    "nm": Decimal("1"), "um": Decimal("1000"),
    "mm": Decimal("1000000"), "m": Decimal("1000000000"),
}
TOLERANCE = Decimal("0.05")


@dataclass(frozen=True)
class FieldConfig:
    pool_enabled: bool = False
    kd_enabled: bool = False
    gold_pool_template: str = "gold_pool_sequence"
    gold_pool_type: str = "gold_pool_type"
    gold_kd_value: str = "gold_kd_value"
    gold_kd_unit: str = "gold_kd_unit"
    pool_sheet: str = "pool_type"
    pool_key: str = "pk"
    pool_value: str = "value"
    pool_evidence: str = "where_in_text"
    kd_sheet: str = "kd"
    kd_key: str = "pk"
    kd_value: str = "raw_values"

    def to_json(self):
        return json.dumps(asdict(self), sort_keys=True)


def _text(value):
    return str(value).strip() if value is not None else ""


def normalized_pool(raw):
    value = _text(raw).upper()
    if not value:
        return None
    value = re.sub(r"^\s*5['′’]\s*[- ]*", "", value)
    value = re.sub(r"[- ]*3['′’]\s*$", "", value)
    value = re.sub(r"\s+", "", value).replace("-", "")
    value = re.sub(r"\[N(\d+)\]", r"N\1", value)
    return value if re.fullmatch(r"(?:[ACGTU]|N[0-9]+)+", value) else None


def pool_type(raw):
    value = " ".join(_text(raw).casefold().replace("-", " ").split())
    aliases = {
        "dna": "DNA", "rna": "RNA",
        "ssdna": "ssDNA", "ssrna": "ssRNA",
        "single stranded dna": "ssDNA", "single stranded rna": "ssRNA",
        "double stranded dna": "dsDNA", "double stranded rna": "dsRNA",
        "dsdna": "dsDNA", "dsrna": "dsRNA",
    }
    if value in aliases:
        return aliases[value]
    hits = set(re.findall(r"\b(?:ssdna|ssrna|dsdna|dsrna)\b", value))
    if len(hits) == 1:
        return aliases[hits.pop()]
    return None


def kd_nm(amount, unit):
    """Parse a single leading numeric Kd; reject censored/range measurements.

    Trailing 'by <method>' or '± <uncertainty>' is allowed for legacy gold.
    Never infer a missing or unknown unit.
    """
    raw = _text(amount)
    unit_raw = _text(unit).replace("μ", "u").replace("µ", "u").casefold()
    if not raw or unit_raw not in UNIT_SCALE:
        return None
    if re.search(r"(?:<|>|≤|≥|~|≈|\bto\b|\bbetween\b)", raw, re.I):
        return None
    match = re.match(r"^\s*(?:Kd\s*:\s*)?("+NUM+r")\b(.*)$", raw, re.I)
    if not match:
        return None
    remainder = match.group(2).strip()
    if remainder and not re.match(r"^(?:±\s*"+NUM+r"\s*)?(?:by\b.*|$)", remainder, re.I):
        return None
    try:
        number = Decimal(match.group(1))*UNIT_SCALE[unit_raw]
        if not number.is_finite() or number <= 0:
            return None
        return number
    except (InvalidOperation, OverflowError):
        return None


def _paper_map(run):
    mapping = defaultdict(set)
    for paper in run.papers:
        mapping[paper.id].add(paper.id)
        for entry in paper.aliases:
            mapping[entry].add(paper.id)
            mapping[alias(entry)].add(paper.id)
    return mapping


def _extract(run, data, sheet, key_col, value_col, kind, evidence_col=""):
    mapping = _paper_map(run)
    output, diagnostics = [], []
    for rownum, item, headers in rows(data, sheet, [key_col, value_col], [evidence_col]):
        key = _text(item.get(key_col))
        targets = mapping.get(key) or mapping.get(alias(key), set())
        if len(targets) != 1:
            diagnostics.append({"field": kind, "source": f"{sheet}!{rownum}",
                                "problem": "Ambiguous/unlinked paper", "paper_key": key})
            continue
        paper = next(iter(targets))
        base = {"field": kind, "paper_id": paper, "source": f"{sheet}!{rownum}",
                "raw": _text(item.get(value_col))}
        if kind == "pool":
            template = normalized_pool(item.get(value_col))
            evidence = _text(item.get(evidence_col)) if evidence_col else ""
            ptype = pool_type(evidence)
            output.append({**base, "id": f"pool:{sheet}:{rownum}", "template": template,
                           "pool_type": ptype, "name": "", "notes": evidence,
                           "valid": bool(template or ptype)})
        else:
            raw = item.get(value_col)
            try:
                entries = parse_items(raw)
            except ValueError:
                entries = [{"_invalid": raw}]
            for i, entry in enumerate(entries):
                item_value = entry if isinstance(entry, dict) else {}
                amount, unit = item_value.get("amount"), item_value.get("unit")
                notes = _text(item_value.get("notes"))
                name_match = re.search(r"(?:\baptamer(?:[_ ]name)?|\bname)\s*[:=]\s*([^,;\n]+)", notes, re.I)
                name = name_match.group(1).strip() if name_match else _text(item_value.get("name"))
                output.append({**base, "id": f"kd:{sheet}:{rownum}:{i}",
                               "raw": raw_json(item_value), "amount": _text(amount),
                               "unit": _text(unit), "nm": kd_nm(amount, unit),
                               "name": name, "notes": notes,
                               "valid": kd_nm(amount, unit) is not None})
    return output, diagnostics


def load_fields(run, gold_bytes, extractor_bytes, config: FieldConfig):
    """Build field inventories once. No fuzzy paper linking or index-paired names."""
    gold = {"pool": [], "kd": []}
    preds = {"pool": [], "kd": []}
    warnings = []
    attempted = {p.id for p in run.papers if p.attempted}
    pool_groups = {}
    for g in run.gold:
        if not g.significant or g.paper_id not in attempted:
            continue
        raw = json.loads(g.source.raw_json)
        if config.kd_enabled:
            val = raw.get(config.gold_kd_value)
            unit = raw.get(config.gold_kd_unit)
            if _text(val):
                gold["kd"].append({
                    "id": "kd:"+g.id, "field": "kd", "paper_id": g.paper_id,
                    "name": g.name, "raw": _text(val), "unit": _text(unit),
                    "nm": kd_nm(val, unit), "source": f"{g.source.sheet}!{g.source.row}",
                    "gold_record_id": g.id, "valid": kd_nm(val, unit) is not None,
                })
        if config.pool_enabled:
            raw_pool = _text(raw.get(config.gold_pool_template))
            raw_type = _text(raw.get(config.gold_pool_type))
            if raw_pool or raw_type:
                template = normalized_pool(raw_pool)
                typ = pool_type(raw_type)
                key = (g.paper_id, template or raw_pool, typ or raw_type)
                if key not in pool_groups:
                    digest = sha256(json.dumps(key).encode()).hexdigest()[:14]
                    pool_groups[key] = {
                        "id": "pool:"+digest, "field": "pool", "paper_id": g.paper_id,
                        "name": "", "raw": raw_pool, "template": template,
                        "pool_type": typ, "source": f"{g.source.sheet}!{g.source.row}",
                        "valid": bool(template or typ),
                    }
    gold["pool"] = list(pool_groups.values())
    if config.pool_enabled:
        items, errors = _extract(run, extractor_bytes, config.pool_sheet, config.pool_key,
                                 config.pool_value, "pool", config.pool_evidence)
        preds["pool"] = items
        warnings.extend(errors)
    if config.kd_enabled:
        items, errors = _extract(run, extractor_bytes, config.kd_sheet, config.kd_key,
                                 config.kd_value, "kd")
        preds["kd"] = items
        warnings.extend(errors)
    return {"gold": gold, "predictions": preds, "warnings": warnings,
            "config": config.to_json(), "run_id": run.run_id}


def _comparison(g, e):
    if g["field"] == "pool":
        return {"exact": bool(g.get("template") and g.get("template") == e.get("template")),
                "tolerant": bool(g.get("template") and g.get("template") == e.get("template")),
                "pool_type_exact": (g.get("pool_type") == e.get("pool_type")
                                    if g.get("pool_type") and e.get("pool_type") else None)}
    a, b = g.get("nm"), e.get("nm")
    if a is None or b is None:
        return {"exact": False, "tolerant": False, "relative_error_pct": None}
    delta = abs(a-b)
    return {"exact": a == b, "tolerant": delta <= TOLERANCE*a,
            "relative_error_pct": float(delta / a * Decimal("100"))}


def field_results(data, actions=()):
    """Return per-field gold outcomes and closed-world metrics.

    Exactly one effective association per gold and extractor. A manual identity
    confirmation never changes the extracted Kd or pool value. Recompute after
    every action; original source and auto decisions remain unchanged.
    """
    results = {}
    for kind in ("pool", "kd"):
        gold, predictions = data["gold"][kind], data["predictions"][kind]
        gs = {g["id"]: g for g in gold}
        es = {e["id"]: e for e in predictions}
        gp, ep = defaultdict(list), defaultdict(list)
        for g in gold: gp[g["paper_id"]].append(g)
        for e in predictions: ep[e["paper_id"]].append(e)
        pairs, reasons = {}, {}
        for pid in sorted(gp):
            g_items, e_items = gp[pid], ep[pid]
            if len(g_items) == 1 and len(e_items) == 1:
                g, e = g_items[0], e_items[0]
                contradictory = (g.get("name") and e.get("name")
                                 and name_key(g["name"]) != name_key(e["name"]))
                if not contradictory:
                    pairs[g["id"]] = e["id"]
                    reasons[g["id"]] = "UNIQUE_PAPER_PAIR"
            elif kind == "kd":
                # Exact explicit aptamer name is identity evidence. Numerical
                # proximity by itself cannot assign a measurement.
                for e in e_items:
                    if not name_key(e.get("name")): continue
                    named = [g for g in g_items if name_key(g.get("name")) == name_key(e.get("name"))]
                    competing = [x for x in e_items if name_key(x.get("name")) == name_key(e.get("name"))]
                    if len(named) == 1 and len(competing) == 1 and named[0]["id"] not in pairs:
                        pairs[named[0]["id"]] = e["id"]
                        reasons[named[0]["id"]] = "EXPLICIT_APTAMER_NAME"
            else:
                # A shared pool contributes one library-level gold observation,
                # not one TP for every aptamer using that library.
                for g in g_items:
                    if not g.get("template"):continue
                    found = [e for e in e_items if e.get("template") == g["template"]]
                    other_gold = [x for x in g_items if x.get("template") == g["template"]]
                    if len(found) == 1 and len(other_gold) == 1:
                        pairs[g["id"]] = found[0]["id"]
                        reasons[g["id"]] = "UNIQUE_EXACT_POOL_TEMPLATE"
        automatic = dict(pairs)
        missing, rejected = set(), set()
        for ev in actions:
            if ev.get("field") != kind: continue
            gid, eid, action = ev.get("gold_id"), ev.get("extractor_id"), ev.get("action")
            if gid not in gs:
                raise ValueError("Reviewed gold record absent from current input")
            if action == "confirm":
                if eid not in es or gs[gid]["paper_id"] != es[eid]["paper_id"]:
                    raise ValueError("Review must select a same-paper prediction")
                if eid in pairs.values() and pairs.get(gid) != eid:
                    raise ValueError("Prediction already assigned; clear that link first")
                pairs[gid] = eid
                reasons[gid] = "HUMAN_CONFIRMED_IDENTITY"
                missing.discard(gid)
                rejected.discard((gid, eid))
            elif action == "missing":
                pairs.pop(gid, None)
                missing.add(gid)
            elif action == "reject":
                if eid not in es or gs[gid]["paper_id"] != es[eid]["paper_id"]:
                    raise ValueError("Unknown or unrelated prediction")
                rejected.add((gid, eid))
                if pairs.get(gid) == eid: pairs.pop(gid, None)
            elif action == "unresolved":
                pairs.pop(gid, None)
                missing.discard(gid)
            else:
                raise ValueError("Unknown field review action")
        if len(set(pairs.values())) != len(pairs):
            raise ValueError("Field review violates one-to-one assignments")
        rows_out, passing = [], 0
        for g in gold:
            eid = pairs.get(g["id"])
            e = es.get(eid) if eid else None
            check = _comparison(g, e) if e else {}
            ok = bool(check.get("tolerant"))
            passing += int(ok)
            rows_out.append({"field": kind, "gold": g, "extractor": e,
                             "status": ("MARKED_MISSING" if g["id"] in missing else
                                        "UNRESOLVED" if e is None else reasons[g["id"]]),
                             "comparison": check, "passes": ok,
                             "auto_extractor_id": automatic.get(g["id"], "")})
        G, E, M, T = len(gold), len(predictions), len(pairs), passing
        results[kind] = {
            "rows": rows_out, "gold": gold, "predictions": predictions,
            "pairs": pairs, "automatic_pairs": automatic,
            "missing": sorted(missing), "rejected": sorted(rejected),
            "pending": len(set(gs)-set(pairs)-missing),
            "G": G, "E": E, "M": M, "T": T,
            "TP": T, "FP": E-T, "FN": G-T,
            "precision": T/E if E else None, "recall": T/G if G else None,
            "f1": 2*T/(E+G) if E+G else None,
            "matched_correctness": T/M if M else None,
            "scope_warning": "Closed-world field counts: unmatched predictions are not independently verified biological FPs.",
        }
    return results
