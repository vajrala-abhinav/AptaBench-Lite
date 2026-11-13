from dataclasses import asdict
from pathlib import Path
import json
import streamlit as st
from .config import RunConfig
from .readers import inspect_workbook,source_bytes,ingest
from .engine import evaluate
from .models import associations,base_run,ReviewedRun
from .scoring import compute_metrics,paper_status,CAVEAT
from .review import commit_event,save_review,import_review,export_review
from .exports import export_audit,export_workbook
from .presentation import alignment_html

ROOT=Path(__file__).resolve().parents[2]
STORE=Path.cwd()/'.local'/'reviews'


@st.cache_data(show_spinner=False,max_entries=4)
def _inspect(data):return inspect_workbook(data)


@st.cache_data(show_spinner=False,max_entries=4)
def _preview(gb,eb,cfg):return ingest(gb,eb,RunConfig(**json.loads(cfg)))


@st.cache_data(show_spinner=False,max_entries=4)
def _evaluate(gb,eb,cfg):return evaluate(gb,eb,RunConfig(**json.loads(cfg)))


def choose(label,headers,candidates,key,optional=False):
    options=(['(none)'] if optional else [])+headers
    default=next((c for c in candidates if c in headers),'(none)' if optional else headers[0])
    selected=st.selectbox(label,options,index=options.index(default),key=key)
    return '' if selected=='(none)' else selected


def configure(gb,eb,gname,ename):
    gi,ei=_inspect(gb),_inspect(eb)
    left,right=st.columns(2)
    with left:
        st.subheader('Gold reference')
        gs=st.selectbox('Gold worksheet',list(gi),key='gs');gh=gi[gs]['headers']
        if not gh:raise ValueError('Gold worksheet has no headers')
        st.dataframe([dict(zip(gh,row)) for row in gi[gs]['preview']],hide_index=True)
        gp=choose('Gold paper ID',gh,['paper_id'],'gp');gk=choose('Gold filename / linking key',gh,['pdf_name','paper_key'],'gk')
        gid=choose('Gold record ID',gh,['record_id','id'],'gid');gseq=choose('Gold sequence',gh,['gold_sequence','sequence'],'gseq')
        gn=choose('Gold aptamer name (optional)',gh,['aptamer_label_optional','name'],'gn',True)
        gt=choose('Gold significance column',gh,['aptamer_type','significance','sequence_status'],'gt')
        gstatus=choose('Gold presence-status column (optional)',gh,['sequence_status'],'gstatus',True)
        significant=st.text_input('Significant labels (comma separated)','significant_sequence',key='significant')
        nonsignificant=st.text_input('Non-significant labels','non_significant_sequence',key='nonsignificant')
        present=st.text_input('Present sequence labels','present',key='present')
    with right:
        st.subheader('Extractor predictions')
        es=st.selectbox('Extractor worksheet',list(ei),index=list(ei).index('aptamer_seq') if 'aptamer_seq' in ei else 0,key='es');eh=ei[es]['headers']
        if not eh:raise ValueError('Extractor worksheet has no headers')
        st.dataframe([dict(zip(eh,row)) for row in ei[es]['preview']],hide_index=True)
        ek=choose('Extractor paper key',eh,['pk','paper_id','paper_key'],'ek');ev=choose('Extractor sequence / value',eh,['value','sequence'],'ev')
        parser=st.selectbox('Extractor cell format',['Structured list of sequence dictionaries','One sequence per row'],key='parser')
        simple=parser=='One sequence per row'
        en=choose('Sequence-row aptamer name (simple tables only)',eh,['name','aptamer_name'],'en',True)
        notes=choose('Sequence-row notes (simple tables only)',eh,['notes'],'notes',True)
        seqkey=st.text_input('Sequence key inside structured items','sequence',key='seqkey')
        st.caption('Names in independent aptamer_name sheets are paper context only. They are never paired by list position. Pool and Kd scoring await separate specifications.')
    with st.expander('Advanced batch scope and filename aliases'):
        attempted=st.text_area('Additional processed paper keys (one per line)',key='attempted')
        suffixes=st.text_input('Known artifact suffixes to remove (comma separated)',key='suffixes')
    split=lambda v:tuple(x.strip() for x in v.split(',') if x.strip())
    # A single significance/status field is explicit; historic type + presence
    # uses two separate columns. No implicit significant status inference.
    cfg=RunConfig(gold_sheet=gs,extractor_sheet=es,gold_paper=gp,gold_key=gk,gold_id=gid,gold_sequence=gseq,gold_name=gn,
        gold_type=gt if gstatus and gstatus!=gt else '',gold_status=gstatus if gstatus and gstatus!=gt else gt,
        significant_values=split(significant),nonsignificant_values=split(nonsignificant),present_values=split(present),
        extractor_key=ek,extractor_value=ev,extractor_name=en if simple else '',extractor_notes=notes if simple else '',
        parser='simple' if simple else 'structured',sequence_key=seqkey,attempted_keys=tuple(x.strip() for x in attempted.splitlines() if x.strip()),
        artifact_suffixes=split(suffixes),gold_filename=gname,extractor_filename=ename)
    return cfg


def metric_display(value,population,tolerance,scope):
    m=compute_metrics(value,population,tolerance,scope)
    st.caption('After human review' if m['review_mode']=='effective' else 'Automatic only')
    fmt=lambda v:'N/A' if v is None else f'{100*v:.2f}%'
    cols=st.columns(3)
    if population=='all':
        for col,label,key in zip(cols,['Precision','Recall','F1'],['precision','recall','f1']):col.metric(label,fmt(m[key]))
        st.info(CAVEAT)
    else:
        cols[0].metric('Matched-pair correctness',fmt(m['matched_correctness']))
        cols[1].metric('Significant-gold recovery',fmt(m['significant_recovery']))
        cols[2].metric('Accepted pairs',m['M'])
    st.write(f"G={m['G']} significant golds · E={m['E']} logical predictions · M={m['M']} accepted pairs · T={m['T']} passing pairs")
    st.caption(f"TP={m['TP']} · FP={m['FP']} · FN={m['FN']} · Pending={m['pending_gold']} · Raw extractor items={m['n_raw_extractor']} · Duplicate suppressed={m['duplicate_suppressed']}")
    if m['significant_unscoreable']:st.warning(f"{m['significant_unscoreable']} significant gold records are unscoreable and excluded from G. Recovery does not establish reference completeness.")
    if m['unattempted_papers']:st.caption(f"{m['unattempted_papers']} unattempted gold papers excluded from attempted-run denominators.")
    if not m['G']:st.warning('No scoreable significant gold sequences in this population.')
    return m


def _commit(value,action,gid,eid,reviewer,note,confirmed=False,target=None):
    current=len(value.events) if isinstance(value,ReviewedRun) else 0
    updated=commit_event(value,action,reviewer,gid,eid,note,target_revision=target,confirmed=confirmed,expected_revision=current)
    save_review(updated,STORE/(base_run(value).run_id+'.json'),expected_revision=current)
    st.session_state['value']=updated
    st.session_state['flash']='Review saved locally; sequence correctness remains determined by the stored alignment.'
    st.rerun()


def paper_detail(value,scope,population="all",tolerance="adaptive"):
    run=base_run(value);attempted=[p for p in run.papers if p.attempted]
    if not attempted:return
    pid=st.selectbox('Paper',[p.id for p in attempted],key='paper')
    paper=next(p for p in attempted if p.id==pid);m=compute_metrics(value,paper_id=pid)
    st.subheader(f'{pid} — Sequence detail')
    st.write(f"Significant golds: {m['G']} · Accepted: {m['M']} · Unresolved: {m['pending_gold']} · Unique/logical extractor predictions: {m['E']}")
    st.caption(' · '.join(paper.aliases));st.write('Evaluation complete' if paper_status(value,paper)=='REVIEW_COMPLETE' else 'Manual review needed')
    resolved=m['G']-m['pending_gold']
    st.progress(resolved/m['G'] if m['G'] else 0,text=f"Review outcomes resolved: {resolved}/{m['G']} (accepted association or reviewed missing)")
    gm={g.id:g for g in run.gold};em={e.id:e for e in run.extractors};am={a.gold_id:a for a in associations(value)}
    missing=set(value.missing) if isinstance(value,ReviewedRun) else set();dm={d.gold_id:d for d in run.decisions}
    status=lambda g:am[g].origin if g in am else 'MARKED_MISSING_HUMAN' if g in missing else dm[g].status
    st.dataframe([{'Gold':g,'Name':gm[g].name,'Status':status(g),'Extractor':am[g].extractor_id if g in am else '',
                   'Length':len(gm[g].sequence.canonical),'Reason':', '.join(am[g].reasons if g in am else dm[g].reasons)} for g in paper.gold_ids],hide_index=True)
    if m['pending_gold'] or m['significant_unscoreable']:
        if st.button(f"Resolve manual review ({m['pending_gold']})",key='resolve'):st.session_state['correction']=True
    correction=st.checkbox('Enable review / correction actions',key='correction')
    left,right=st.columns(2)
    with left:
        st.markdown('**Significant gold records**')
        gid=st.selectbox('Gold record',list(paper.gold_ids),format_func=lambda g:f'{g} · {gm[g].name} · {len(gm[g].sequence.canonical)} nt',key=f'gold-{pid}') if paper.gold_ids else None
    logical=list(paper.logical_extractor_ids)
    with right:
        st.markdown('**Extractor records**')
        # Include suppressed/invalid records for inspection; backend rejects
        # invalid identity transactions and prevents double-use.
        all_ids=list(paper.extractor_ids)
        def availability(e):
            owner=next((a.gold_id for a in associations(value) if a.extractor_id==e),None)
            return 'Assigned to '+owner if owner else 'Available' if e in logical else 'Duplicate-suppressed / invalid'
        st.dataframe([{'Extractor':e,'Name':em[e].name,'Availability':availability(e)} for e in all_ids],hide_index=True)
        def ext_label(e):
            return f'{e} · {em[e].name or "unnamed"} · {len(em[e].sequence.canonical or "")} nt'
        suggestions=sorted((c for c in run.candidates if c.gold_id==gid),key=lambda c:(not c.name_support,c.core.distance/c.core.gold_end,c.whole.distance/c.whole.gold_end,c.id))
        auto_map={a.gold_id:a for a in run.automatic}
        preferred=auto_map[gid].extractor_id if gid in auto_map else suggestions[0].extractor_id if suggestions else None
        default_index=all_ids.index(preferred) if preferred in all_ids else 0
        eid=st.selectbox('Extractor record',all_ids,index=default_index,format_func=ext_label,key=f'ext-{pid}-{gid}') if all_ids else None
    c=next((c for c in run.candidates if c.gold_id==gid and c.extractor_id==eid),None)
    if gid:
        with st.expander('Gold raw/canonical data and source'):
            st.json(asdict(gm[gid]))
    if eid:
        with st.expander('Extractor raw data, provenance and duplicate members'):
            st.json(asdict(em[eid]));st.json([asdict(d) for d in run.duplicates if eid in d.members])
    if c:
        trace=c.core if scope=='core' else c.whole
        st.markdown(alignment_html(trace),unsafe_allow_html=True)
        st.caption('Green = matching bases · Yellow = insertion/deletion (− gap) · Red = substitution · Gray = free extractor flank')
        st.write(f'Core edits: {c.core.distance} · Whole edits: {c.whole.distance} · Allowed edits: {c.budget} · Completion: {trace.completion():.2f}%')
        st.write(f'Fitted interval [{c.core.extractor_start}, {c.core.extractor_end}) · Free flanks: {len(c.core.left_flank)} / {len(c.core.right_flank)}')
        st.json({'counts':trace.counts,'strict_core':c.passes('strict','core'),'adaptive_core':c.passes('adaptive','core'),
                 'strict_whole':c.passes('strict','whole'),'adaptive_whole':c.passes('adaptive','whole')},expanded=False)
        if c.core.distance>c.budget:st.warning('Outside tolerance. Confirming identity will not make this sequence correct.')
        with st.expander('Why this match? Candidate rankings and competitors'):
            edges=[x for x in run.candidates if x.paper_id==pid and (x.gold_id==gid or x.extractor_id==eid)]
            edges=sorted(edges,key=lambda x:(not x.name_support,x.core.distance/max(1,x.core.gold_end),x.whole.distance/max(1,x.whole.gold_end),x.id))
            st.dataframe([{'Rank':i+1,'Gold':x.gold_id,'Extractor':x.extractor_id,'Core edits':x.core.distance,'Whole edits':x.whole.distance,
                           'Name supports':x.name_support,'Name conflicts':x.name_conflict,'Stage':x.stage,'Reasons':', '.join(x.reasons)} for i,x in enumerate(edges)],hide_index=True)
    elif gid and eid:st.info('No scored comparison: this item is suppressed or has unsupported source syntax. Inspect its raw provenance.')
    if not correction or not gid:return
    reviewer=st.text_input('Reviewer identity',key='reviewer');note=st.text_input('Review note / reassignment reason',key='review-note')
    confirm=st.checkbox('I explicitly confirm the affected-association changes',key='explicit-confirm')
    affected=[asdict(a) for a in associations(value) if a.gold_id==gid or a.extractor_id==eid]
    st.caption('Current associations affected by the selected correction:');st.json(affected,expanded=False)
    if any(x.gold_id==gid and x.viable for x in run.candidates) and gid not in missing:
        st.warning('Plausible candidates remain in the graph. Marking this gold missing explicitly records that no acceptable counterpart exists; it does not improve recovery.')
    if c:
        proposed=commit_event(value,'REASSIGN',reviewer or 'PREVIEW',gid,eid,note or 'Preview only',confirmed=True)
        before=compute_metrics(value,population,tolerance,scope);after=compute_metrics(proposed,population,tolerance,scope)
        st.caption('Reassignment preview under the selected scoring view (not saved):')
        st.json({key:{'before':before[key],'after':after[key]} for key in ('M','T','FP','FN','pending_gold')},expanded=False)
    buttons=st.columns(3)
    actions=[('Confirm association','CONFIRM_ASSOCIATION'),('Reject candidate','REJECT_PAIR'),('Mark gold missing','MARK_GOLD_MISSING'),
             ('Leave unresolved','LEAVE_UNRESOLVED'),('Reassign explicitly','REASSIGN')]
    for i,(label,action) in enumerate(actions):
        disabled=not reviewer.strip() or (action in ('CONFIRM_ASSOCIATION','REASSIGN','REJECT_PAIR') and c is None)
        if buttons[i%3].button(label,disabled=disabled,key=action):
            try:_commit(value,action,gid,eid or '',reviewer,note,confirm)
            except ValueError as exc:st.error(str(exc))
    if isinstance(value,ReviewedRun) and value.events:
        revisions=[e.revision for e in value.events if e.action!='UNDO']
        target=st.selectbox('Action revision to undo',revisions,key='undo-target')
        if st.button('Undo selected action',disabled=not reviewer.strip()):
            try:_commit(value,'UNDO',gid,'',reviewer,note,target=target)
            except ValueError as exc:st.error(str(exc))


def main():
    st.set_page_config(page_title='AptaBench Lite',layout='wide')
    st.title('AptaBench Lite');st.caption('Significant-reference sequence evaluation · Local single-user review')
    with st.expander('Privacy and scientific scope'):
        st.write('Evaluation runs locally without external APIs. Do not expose this server publicly. Only significant gold sequences are scored. Pool/Kd scoring and biological identity guarantees are outside this version.')
    st.subheader('Upload & configure')
    st.multiselect('Fields to evaluate',['Sequence'],default=['Sequence'],disabled=True)
    left,right=st.columns(2)
    gu=left.file_uploader('Gold workbook (.xlsx)',type=['xlsx'],key='gold-upload')
    eu=right.file_uploader('Extractor workbook (.xlsx)',type=['xlsx'],key='extractor-upload')
    demo=st.checkbox('Use synthetic example workbooks',key='demo')
    if gu and eu:gb,eb,gname,ename=gu.getvalue(),eu.getvalue(),gu.name,eu.name
    elif demo:
        gb=(ROOT/'examples/gold.xlsx').read_bytes();eb=(ROOT/'examples/extractor.xlsx').read_bytes();gname='gold.xlsx';ename='extractor.xlsx'
    else:
        st.info('Choose both workbooks, or try the synthetic examples.');return
    try:
        source_bytes(gb);source_bytes(eb)
        with st.expander('Worksheets & column mappings',expanded='value' not in st.session_state):
            cfg=configure(gb,eb,gname,ename)
        gold,ext,attempted,diags=_preview(gb,eb,cfg.to_json())
        st.subheader('Input validation preview')
        st.write(f'{len(gold)} gold rows · {sum(g.significant for g in gold)} significant records · {sum(len(g.sequence.canonical or "") for g in gold if g.significant)} significant bases · {len(attempted)} linked attempted papers · {len(ext)} raw extractor items')
        st.dataframe([{'Paper':p,'Extractor items':sum(e.paper_id==p for e in ext)} for p in attempted],hide_index=True)
        if diags:
            with st.expander(f'Validation diagnostics ({len(diags)})',expanded=not attempted):st.dataframe([asdict(d) for d in diags],hide_index=True)
        if st.button('Run evaluation',type='primary',disabled=not attempted):
            with st.spinner('Evaluating fixed sequence associations…'):
                run=_evaluate(gb,eb,cfg.to_json());path=STORE/(run.run_id+'.json')
                value=import_review(run,path.read_bytes()) if path.exists() else run
                st.session_state['value']=value;st.session_state['input-key']=(gb,eb,cfg.to_json())
    except (ValueError,OSError) as exc:st.error(str(exc));return
    if 'value' not in st.session_state:return
    if st.session_state.get('input-key')!=(gb,eb,cfg.to_json()):
        st.warning('Inputs or mapping changed. Run evaluation to establish a new fingerprint; previous review remains stored.');return
    value=st.session_state['value'];run=base_run(value)
    if 'flash' in st.session_state:st.success(st.session_state.pop('flash'))
    st.header('Overview');st.caption(f'Run {run.run_id[:16]} · Policy {run.policy_version}')
    cols=st.columns(3)
    population=cols[0].radio('Population',['All sequences','Matched only'],key='population')
    tolerance=cols[1].radio('Tolerance',['Strict','Adaptive tolerant'],index=1,key='tolerance')
    scope=cols[2].radio('Sequence comparison',['Whole string','Core matching'],index=1,key='scope')
    pop='all' if population=='All sequences' else 'matched';tol='strict' if tolerance=='Strict' else 'adaptive';sc='whole' if scope=='Whole string' else 'core'
    metrics=metric_display(value,pop,tol,sc)
    st.dataframe([{'Paper':p.id,'Attempted':p.attempted,'Status':paper_status(value,p),**{k:v for k,v in compute_metrics(value,pop,tol,sc,p.id).items() if k in ('G','E','M','T','pending_gold','significant_recovery')}} for p in run.papers],hide_index=True)
    paper_detail(value,sc,pop,tol)
    st.header('Export & resume')
    st.caption('Every committed action is autosaved under .local/reviews. Download a portable review backup before moving machines. Re-upload the identical inputs and mappings to resume.')
    try:
        st.download_button('Download Excel',export_workbook(value,metrics),'aptabench-evaluation.xlsx',key='download-xlsx')
        st.download_button('Download JSON audit',export_audit(value,metrics),'aptabench-audit.json',mime='application/json',key='download-audit')
        st.download_button('Download review state',export_review(value),'aptabench-review.json',mime='application/json',key='download-review')
        st.download_button('Download mapping configuration',cfg.to_json(),'aptabench-config.json',mime='application/json')
    except ValueError as exc:st.error(str(exc))
    imported=st.file_uploader('Restore review-state JSON',type=['json'],key='review-upload')
    if imported and st.button('Restore review state'):
        try:
            restored=import_review(run,imported.getvalue())
            path=STORE/(run.run_id+'.json')
            current=len(import_review(run,path.read_bytes()).events) if path.exists() else 0
            # Import is explicit; never silently truncate existing history.
            old_events=value.events if isinstance(value,ReviewedRun) else ()
            if restored.events[:len(old_events)]!=old_events:raise ValueError('Imported history conflicts with current review; use a fresh session/store to inspect it')
            save_review(restored,path,expected_revision=current);st.session_state['value']=restored;st.rerun()
        except ValueError as exc:st.error(str(exc))
