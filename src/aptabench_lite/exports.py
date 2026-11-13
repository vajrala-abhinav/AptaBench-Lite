"""Excel and JSON projections of canonical results; no scientific computation."""
from dataclasses import asdict
from io import BytesIO
import json
import xlsxwriter
from .models import base_run,associations,ReviewedRun
from .scoring import compute_metrics,paper_status,CAVEAT
from .presentation import COLORS


def audit_dict(value,metrics=None):
    run=base_run(value)
    return {'schema_version':'lite-audit-1','run':asdict(run),'metadata':json.loads(run.metadata_json),
            'configuration':json.loads(run.config_json),'selected_metrics':metrics or compute_metrics(value),
            'automatic_metrics':{f'{pop}/{tol}/{scope}':compute_metrics(run,pop,tol,scope) for pop in ('all','matched') for tol in ('strict','adaptive') for scope in ('whole','core')},
            'effective_metrics':{f'{pop}/{tol}/{scope}':compute_metrics(value,pop,tol,scope) for pop in ('all','matched') for tol in ('strict','adaptive') for scope in ('whole','core')},
            'effective_associations':[asdict(a) for a in associations(value)],
            'review_events':[asdict(e) for e in value.events] if isinstance(value,ReviewedRun) else [],
            'marked_missing':list(value.missing) if isinstance(value,ReviewedRun) else [],
            'rejected_pairs':list(value.rejected) if isinstance(value,ReviewedRun) else [],'methodology':CAVEAT}


def export_audit(value,metrics=None):
    return json.dumps(audit_dict(value,metrics),ensure_ascii=False,indent=2,default=str,allow_nan=False).encode()


def export_workbook(value,metrics=None):
    run=base_run(value);metrics=metrics or compute_metrics(value)
    if metrics.get('review_mode')!=compute_metrics(value)['review_mode']:raise ValueError('Metrics review mode does not match result')
    # Reaggregate requested view only; fixed associations/traces remain untouched.
    expected=compute_metrics(value,metrics['population'],metrics['tolerance'],metrics['sequence_scope'])
    if metrics!=expected:raise ValueError('Metrics do not match canonical result/view')
    out=BytesIO();wb=xlsxwriter.Workbook(out,{'in_memory':True,'strings_to_formulas':False,'strings_to_urls':False})
    header=wb.add_format({'bold':True,'bg_color':'#DDE9F4','text_wrap':True})
    wrap=wb.add_format({'text_wrap':True,'valign':'top'});mono=wb.add_format({'font_name':'Consolas','font_size':10})
    colors={op:wb.add_format({'font_color':{'MATCH':'#166534','INSERTION':'#854D0E','DELETION':'#854D0E','SUBSTITUTION':'#991B1B','FREE_EXTRACTOR_FLANK':'#64748B'}[op], 'font_name':'Consolas'}) for op in COLORS}
    def sheet(name,headers):
        ws=wb.add_worksheet(name);ws.freeze_panes(1,0);ws.write_row(0,0,headers,header);ws.set_column(0,len(headers)-1,22)
        return ws
    def safe(v):
        if isinstance(v,(dict,list,tuple)):v=json.dumps(v,default=str,ensure_ascii=False)
        return '' if v is None else v
    def write_row(ws,row,values):
        for col,v in enumerate(values):
            v=safe(v)
            if isinstance(v,str) and len(v)>32767:raise ValueError('Excel cell exceeds 32767 characters; use JSON audit for full raw data')
            ws.write(row,col,v)
    overview=sheet('Overview',['Metric','Value'])
    for row,(key,val) in enumerate(metrics.items(),1):write_row(overview,row,[key,val])
    overview.set_column(0,0,30);overview.set_column(1,1,100)
    papers=sheet('Papers',['paper_id','G','E','M','T','pending','status','precision','recall','F1'])
    for row,p in enumerate(run.papers,1):
        m=compute_metrics(value,metrics['population'],metrics['tolerance'],metrics['sequence_scope'],p.id)
        write_row(papers,row,[p.id,m['G'],m['E'],m['M'],m['T'],m['pending_gold'],paper_status(value,p),m['precision'],m['recall'],m['f1']])
    seq=sheet('Sequence',['paper_id','gold_id','extractor_id','status','curated_name','extractor_name','gold_raw','gold_canonical','extractor_raw','extractor_canonical','gold_length','extractor_length','core_d','whole_d','budget','strict_core','adaptive_core','strict_whole','adaptive_whole','candidate_id','reasons','gold_source','extractor_source','alignment_detail'])
    detail=sheet('Alignment Detail',['candidate_id','sequence','aligned 5prime to 3prime','operations','distance','gold_start','gold_end','extractor_start','extractor_end','optimal_intervals'])
    detail.set_column(2,2,100)
    cm={c.id:c for c in run.candidates};em={e.id:e for e in run.extractors};am={a.gold_id:a for a in associations(value)};dm={d.gold_id:d for d in run.decisions};missing=set(value.missing) if isinstance(value,ReviewedRun) else set()
    row=1;arow=1
    for g in run.gold:
        if not g.significant or not g.sequence.canonical:continue
        a=am.get(g.id);e=em[a.extractor_id] if a else None;c=cm[a.candidate_id] if a else None
        decision=dm[g.id]
        status=a.origin if a else 'MARKED_MISSING_HUMAN' if g.id in missing else decision.status
        write_row(seq,row,[g.paper_id,g.id,e.id if e else '',status,g.name,e.name if e else '',g.sequence.raw,g.sequence.canonical,
            e.sequence.raw if e else '',e.sequence.canonical if e else '',len(g.sequence.canonical),len(e.sequence.canonical) if e else '',
            c.core.distance if c else '',c.whole.distance if c else '',c.budget if c else '',
            c.passes('strict','core') if c else '',c.passes('adaptive','core') if c else '',c.passes('strict','whole') if c else '',c.passes('adaptive','whole') if c else '',
            c.id if c else '',a.reasons if a else decision.reasons,asdict(g.source),asdict(e.source) if e else '',arow+1 if c else ''])
        if c:
            trace=c.core if metrics['sequence_scope']=='core' else c.whole
            for label,string in [('Gold',trace.aligned_gold),('Extractor',trace.aligned_extractor)]:
                write_row(detail,arow,[c.id,label,'',trace.operations,trace.distance,trace.gold_start,trace.gold_end,trace.extractor_start,trace.extractor_end,trace.optimal_interval_count])
                # Rich text segments share the exact stored operation order.
                segments=[]
                for char,op in zip(string,trace.operations):segments.extend((colors[op],char))
                if len(string)==1:detail.write(arow,2,string,colors[trace.operations[0]])
                elif segments:detail.write_rich_string(arow,2,*segments,mono)
                arow+=1
        row+=1
    history=sheet('Review History',['revision','action','reviewer','timestamp','gold_id','extractor_id','note','target_revision','confirmed'])
    if isinstance(value,ReviewedRun):
        for row,event in enumerate(value.events,1):write_row(history,row,list(asdict(event).values()))
    info=sheet('Run Info',['Key','Value']);info.set_column(1,1,110)
    fields={'run_id':run.run_id,'policy_version':run.policy_version,'schema_version':run.schema_version,'gold_sha256':run.gold_sha256,'extractor_sha256':run.extractor_sha256,
        'configuration':json.loads(run.config_json),'runtime':json.loads(run.metadata_json),'attempted_papers':[p.id for p in run.papers if p.attempted],
        'automatic_associations':[asdict(a) for a in run.automatic], 'automatic_metrics':compute_metrics(run,metrics['population'],metrics['tolerance'],metrics['sequence_scope']),
        'methodology':CAVEAT}
    for row,(k,v) in enumerate(fields.items(),1):write_row(info,row,[k,v])
    validation=sheet('Validation',['code','message','source','record_id','severity','fix'])
    for row,d in enumerate(run.diagnostics,1):write_row(validation,row,list(asdict(d).values()))
    inventory=sheet('Extractor Inventory',['extractor_id','paper_id','raw','canonical','name','name_source','source','duplicate_group','logical_prediction'])
    for row,e in enumerate(run.extractors,1):
        group=next((d for d in run.duplicates if e.id in d.members),None)
        write_row(inventory,row,[e.id,e.paper_id,e.sequence.raw,e.sequence.canonical,e.name,e.name_source,asdict(e.source),group.id if group else '',bool(group and e.id in group.representatives)])
    wb.close();return out.getvalue()
