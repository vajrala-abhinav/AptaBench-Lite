"""Configurable safe Excel ingestion. No formulas executed, source bytes unchanged."""
from __future__ import annotations
import ast
from collections import Counter, defaultdict
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from zipfile import ZipFile, BadZipFile
from time import perf_counter
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from .models import Record,Source,Diagnostic
from .normalization import normalize,name_key

MAX_BYTES=20*1024*1024
MAX_CELL=100_000
MAX_SEQUENCE=2000


def source_bytes(value):
    data=Path(value).read_bytes() if isinstance(value,(str,Path)) else bytes(value)
    if len(data)>MAX_BYTES:raise ValueError('Workbook exceeds 20 MiB upload limit')
    try:
        with ZipFile(BytesIO(data)) as z:
            if sum(x.file_size for x in z.infolist())>100*1024*1024:raise ValueError('Expanded workbook exceeds 100 MiB safety limit')
    except BadZipFile as exc:raise ValueError('Invalid .xlsx ZIP workbook') from exc
    return data


def workbook(data):
    try:return load_workbook(BytesIO(data),read_only=True,data_only=False,keep_links=False)
    except Exception as exc:raise ValueError('Cannot read .xlsx workbook: '+type(exc).__name__) from exc


def text(value):return str(value).strip() if value is not None else ''


def raw_json(value):return json.dumps(value,default=str,ensure_ascii=False,sort_keys=True,allow_nan=False)


def inspect_workbook(value):
    book=workbook(source_bytes(value));result={}
    try:
        for sheet in book:
            rows=sheet.iter_rows(values_only=True)
            headers=next(rows,())
            result[sheet.title]={'headers':[text(x) for x in headers], 'rows':max(0,(sheet.max_row or 1)-1),
                                 'preview':[[text(x) for x in r] for _,r in zip(range(3),rows)]}
    finally:book.close()
    return result


def rows(data,sheet,required,optional):
    book=workbook(data)
    try:
        if sheet not in book.sheetnames:raise ValueError(f'Worksheet {sheet!r} absent; select an available sheet')
        ws=book[sheet];iterator=ws.iter_rows(values_only=True); headers=[text(x) for x in next(iterator,())]
        for field in required:
            if not field or headers.count(field)!=1:raise ValueError(f'Select one unique header for required column {field!r} in {sheet}')
        for field in optional:
            if field and headers.count(field)!=1:raise ValueError(f'Optional column {field!r} absent or duplicated in {sheet}')
        if len(headers)>500:raise ValueError('More than 500 columns; select a smaller worksheet')
        for row_no,values in enumerate(iterator,2):
            if row_no>10001:raise ValueError('Worksheet exceeds 10,000 row safety limit')
            if not any(v is not None for v in values):continue
            yield row_no,dict(zip(headers,values)),headers
    finally:book.close()


def parse_items(raw):
    if raw is None or raw=='':return []
    if not isinstance(raw,str):raise ValueError('Structured value must be JSON/Python literal text')
    if len(raw)>MAX_CELL:raise ValueError('Structured cell exceeds 100,000 characters')
    # Bound nesting before either parser; quoted brackets are ignored.
    depth=0;quote=None;escaped=False
    for c in raw:
        if escaped:escaped=False;continue
        if c=='\\' and quote:escaped=True;continue
        if quote:
            if c==quote:quote=None
            continue
        if c in "\"'":quote=c
        elif c in '[{(':
            depth+=1
            if depth>12:raise ValueError('Structured nesting exceeds 12 levels')
        elif c in ']})':depth-=1
    try:obj=json.loads(raw)
    except (ValueError,RecursionError):
        try:obj=ast.literal_eval(raw)
        except (ValueError,SyntaxError,MemoryError,RecursionError) as exc:raise ValueError('Malformed structured value; use list of sequence dictionaries') from exc
    if isinstance(obj,dict):obj=[obj]
    if not isinstance(obj,list):raise ValueError('Structured value must contain a list/dictionary, not a scalar')
    if len(obj)>1000:raise ValueError('More than 1000 items in one cell')
    return obj


def alias(key,suffixes=()):
    key=text(key)
    if key.lower().endswith('.pdf'):key=key[:-4]
    for suffix in suffixes:
        if suffix and key.endswith(suffix):key=key[:-len(suffix)]
    return key.strip() # no casefold/fuzzy/transliteration


def ingest(gold_bytes,extractor_bytes,config,_timings=None):
    def normalize_timed(raw):
        start=perf_counter();result=normalize(raw)
        if _timings is not None:_timings['normalization_s']=_timings.get('normalization_s',0)+perf_counter()-start
        return result
    diagnostics=[];gold=[];ext=[];seen=set();previous={};raw_index=defaultdict(set);alias_index=defaultdict(set)
    def issue(code,message,source='',rid='',severity='warning',fix='Inspect source annotations or mapping.'):
        diagnostics.append(Diagnostic(code,message,source,rid,severity,fix))
    required=[config.gold_paper,config.gold_key,config.gold_id,config.gold_sequence,config.gold_status]
    optional=[config.gold_name,config.gold_type]
    for row_no,r,h in rows(gold_bytes,config.gold_sheet,required,optional):
        pid,rid,key=text(r.get(config.gold_paper)),text(r.get(config.gold_id)),text(r.get(config.gold_key))
        loc=f'{config.gold_sheet}!{get_column_letter(h.index(config.gold_sequence)+1)}{row_no}'
        if not pid or not rid:
            issue('MISSING_ID','Gold requires paper and record IDs',loc,severity='error')
            fallback='INVALID-GOLD-'+sha256(raw_json([row_no,r]).encode()).hexdigest()[:20]
            marker=text(r.get(config.gold_type or config.gold_status))
            normalized=replace(normalize_timed(r.get(config.gold_sequence)),canonical=None,status='unscoreable',warnings=('MISSING_ID',))
            gold.append(Record(fallback,pid or None,key,normalized,text(r.get(config.gold_name)),'gold_curated_label',
                Source(Path(config.gold_filename).name,config.gold_sheet,row_no,loc.split('!')[1],None,raw_json(r)),
                marker in config.significant_values,'INVALID_ID'))
            continue
        if rid in seen:raise ValueError(f'Duplicate gold record_id {rid!r}; disambiguate source IDs')
        seen.add(rid)
        if key:previous[pid]=key
        elif pid in previous:
            key=previous[pid];issue('GOLD_KEY_PROPAGATED','Inherited preceding filename from same paper only',loc,rid)
        else:issue('GOLD_KEY_MISSING','Gold filename missing with no preceding same-paper key',loc,rid,'error')
        if key:raw_index[key].add(pid);alias_index[alias(key,config.artifact_suffixes)].add(pid)
        raw_index[pid].add(pid);alias_index[pid].add(pid)
        marker=text(r.get(config.gold_type or config.gold_status))
        significant=marker in config.significant_values
        status='SIGNIFICANT' if significant else 'EXCLUDED_NONSIGNIFICANT' if marker in config.nonsignificant_values else 'UNKNOWN_SIGNIFICANCE'
        if status=='UNKNOWN_SIGNIFICANCE':issue(status,f'Unrecognized significance marker {marker!r}',loc,rid,'error','Map explicit significant/non-significant labels.')
        normalized=normalize_timed(r.get(config.gold_sequence))
        if normalized.canonical and len(normalized.canonical)>MAX_SEQUENCE:raise ValueError(f'Sequence at {loc} exceeds 2000 nt safety limit')
        present=(not config.gold_type) or text(r.get(config.gold_status)) in config.present_values
        if significant and not present:
            normalized=replace(normalized,canonical=None,status='unscoreable',warnings=normalized.warnings+('GOLD_STATUS_NOT_PRESENT',))
        if significant and normalized.status!='valid':issue('SIGNIFICANT_UNSCOREABLE' if not normalized.canonical else 'SIGNIFICANT_SEQUENCE_REVIEW',','.join(normalized.warnings),loc,rid)
        gold.append(Record(rid,pid,key,normalized,text(r.get(config.gold_name)),'gold_curated_label',
            Source(Path(config.gold_filename).name,config.gold_sheet,row_no,loc.split('!')[1],None,raw_json(r)),significant,status))
    attempted=set();occurrence=Counter();linkage={}
    def link(key):
        targets=raw_index.get(key) or alias_index.get(alias(key,config.artifact_suffixes),set())
        if len(targets)==1:
            pid=next(iter(targets));attempted.add(pid);linkage[key]=pid;return pid
        code='PAPER_LINK_AMBIGUOUS' if targets else 'PAPER_UNLINKED'
        issue(code,f'Extractor key {key!r} links to {len(targets)} gold papers',severity='error',fix='Correct identifiers or use an unambiguous paper ID.')
        linkage[key]=None;return None
    for key in config.attempted_keys:link(text(key))
    req=[config.extractor_key,config.extractor_value];opt=[config.extractor_name,config.extractor_notes]
    for row_no,r,h in rows(extractor_bytes,config.extractor_sheet,req,opt):
        key=text(r.get(config.extractor_key));loc=f'{get_column_letter(h.index(config.extractor_value)+1)}{row_no}'
        pid=linkage.get(key) if key in linkage else link(key)
        raw=r.get(config.extractor_value)
        try:
            items=parse_items(raw) if config.parser=='structured' else [{config.sequence_key:raw}]
        except ValueError as exc:
            issue('MALFORMED_VALUE',str(exc),f'{config.extractor_sheet}!{loc}',severity='error',fix='Use valid JSON list of dictionaries or select simple-table parser.')
            items=[{'_invalid_source_value':raw}]
        if not items:issue('ATTEMPTED_EMPTY','Present paper row has zero extracted items',f'{config.extractor_sheet}!{loc}')
        for index,item in enumerate(items):
            valid_dict=isinstance(item,dict)
            sequence=item.get(config.sequence_key) if valid_dict else None
            notes=text(item.get('notes')) if valid_dict else ''
            name='';name_source=''
            if valid_dict:
                for k in config.name_keys:
                    if isinstance(item.get(k),str) and item[k].strip():name=item[k];name_source='sequence_item';break
            if config.parser=='simple':
                name=text(r.get(config.extractor_name));notes=text(r.get(config.extractor_notes));name_source='sequence_row' if name else ''
            if not name and notes:
                found=re.search(r'(?i)\b(?:aptamer(?:[_ ]name)?|name)\s*[:=]\s*([^;\n,]+)',notes)
                if found:name=found.group(1).strip();name_source='sequence_item_note_explicit'
            if not valid_dict or config.sequence_key not in item:issue('INVALID_ITEM','Item must be dictionary with configured sequence key',f'{config.extractor_sheet}!{loc}[{index}]')
            normalized=normalize_timed(sequence)
            if normalized.canonical and len(normalized.canonical)>MAX_SEQUENCE:raise ValueError(f'Sequence at {loc}[{index}] exceeds 2000 nt')
            fingerprint=sha256(raw_json([key,item,name]).encode()).hexdigest()[:20]
            occurrence[fingerprint]+=1;eid=f'E-{fingerprint}-{occurrence[fingerprint]}'
            source=Source(Path(config.extractor_filename).name,config.extractor_sheet,row_no,loc,index,raw_json({'item':item,'row':r}))
            ext.append(Record(eid,pid,key,normalized,name,name_source,source,notes=notes))
            if normalized.status!='valid':issue('EXTRACTOR_SEQUENCE_REVIEW',','.join(normalized.warnings),f'{config.extractor_sheet}!{loc}[{index}]',eid)
    if not gold:issue('EMPTY_GOLD','No nonempty gold rows',severity='error')
    if not attempted:issue('NO_LINKED_ATTEMPTED_PAPERS','No applicable benchmark population; correct paper linkage',severity='error')
    return tuple(gold),tuple(ext),tuple(sorted(attempted)),tuple(diagnostics)
