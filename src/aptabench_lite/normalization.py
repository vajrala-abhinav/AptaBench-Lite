"""Lossless conservative forward-base normalization (master §6)."""
import re
from .models import Normalized

BASES = frozenset("ACGTURYSWKMBDHVN")
LABELS = re.compile(r"^\s*5['′’]\s*-\s*(.*?)\s*-\s*3['′’]\s*$", re.DOTALL)


def name_key(raw):
    return " ".join(str(raw or "").split()).casefold()


def normalize(raw):
    if raw is None or isinstance(raw, str) and not raw.strip():
        return Normalized(raw, None, "missing", warnings=("MISSING_SEQUENCE",))
    if not isinstance(raw, str):
        return Normalized(raw, None, "invalid", warnings=("NONSTRING_SEQUENCE",))
    part, start, changes = raw, 0, []
    match = LABELS.fullmatch(raw)
    if match:
        part, start = match.group(1), match.start(1)
        changes.append("strip_paired_5prime_3prime_labels")
    offsets = tuple(start+i for i,c in enumerate(part) if not c.isspace())
    text = "".join(part[i-start] for i in offsets)
    if any(ord(c)>127 for c in text):
        return Normalized(raw,None,"unsupported",warnings=("SUSPICIOUS_UNICODE",))
    if any(c.upper() not in BASES for c in text):
        return Normalized(raw,None,"unsupported",warnings=("INVALID_CHEMICAL_SEQUENCE",))
    if not text:
        return Normalized(raw,None,"missing",warnings=("MISSING_SEQUENCE",))
    if any(c.isspace() for c in part): changes.append("remove_whitespace")
    if text != text.upper(): changes.append("uppercase")
    canonical = text.upper()
    warnings=[]
    if set(canonical)-set("ACGTU"):warnings.append("IUPAC_LITERAL_REVIEW")
    if "T" in canonical and "U" in canonical:warnings.append("MIXED_T_U_REVIEW")
    return Normalized(raw,canonical,"review" if warnings else "valid",tuple(changes),offsets,tuple(warnings))
