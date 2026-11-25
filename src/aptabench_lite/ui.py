from dataclasses import asdict
import os
from time import perf_counter
from .performance import Capture, measured
from pathlib import Path
import json
import streamlit as st
from .config import RunConfig
from .readers import inspect_workbook,source_bytes,ingest
from .engine import evaluate
from .models import associations,base_run,ReviewedRun
from .scoring import compute_metrics,paper_status,CAVEAT,review_diagnostics
from .review import commit_event,save_review,import_review,export_review
from .exports import export_audit,export_workbook
from .presentation import alignment_html
from .field_eval import FieldConfig, load_fields, field_results
from .field_review import fingerprint as fields_fingerprint, from_bytes as field_review_from_bytes, save as save_field_review, append as append_field_review, to_bytes as field_review_to_bytes, replay as replay_field_review

ROOT=Path(__file__).resolve().parents[2]
STORE=Path.cwd()/'.local'/'reviews'


@st.cache_data(show_spinner=False,max_entries=4)
def _inspect(data):return inspect_workbook(data)


@st.cache_data(show_spinner=False,max_entries=4)
def _preview(gb,eb,cfg):return ingest(gb,eb,RunConfig(**json.loads(cfg)))


@st.cache_data(show_spinner=False,max_entries=4)
def _evaluate(gb,eb,cfg):return evaluate(gb,eb,RunConfig(**json.loads(cfg)))


@st.cache_data(show_spinner=False,max_entries=4)
def _load_fields(gb,eb,run_id,cfg,_run):
    # Hash source bytes/config/identity, not the large candidate graph. _run is
    # the already evaluated immutable run and is used only on a cache miss.
    if _run.run_id!=run_id:raise ValueError('Optional field run identity mismatch')
    return load_fields(_run,gb,eb,FieldConfig(**json.loads(cfg)))



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



def configure_extra_fields(gb, eb, gold_sheet):
    gi, ei = _inspect(gb), _inspect(eb)
    headers = gi[gold_sheet]["headers"]
    with st.expander("Optional Pool and Kd evaluation"):
        st.caption("Separate field scores; sequence matching remains unchanged.")
        left,right = st.columns(2)
        pool_on=left.checkbox("Evaluate pool",key="evaluate-pool")
        kd_on=right.checkbox("Evaluate Kd",key="evaluate-kd")
        opts={}
        if pool_on:
            st.markdown("**Pool — distinct library template per paper**")
            opts["gold_pool_template"]=choose("Gold pool template",headers,["gold_pool_sequence"],"pool-gold")
            opts["gold_pool_type"]=choose("Gold pool type",headers,["gold_pool_type"],"pool-type",True)
            opts["pool_sheet"]=st.selectbox("Extractor pool worksheet",list(ei),index=list(ei).index("pool_type") if "pool_type" in ei else 0,key="pool-sheet")
            h=ei[opts["pool_sheet"]]["headers"]
            opts["pool_key"]=choose("Extractor pool paper ID",h,["pk","paper_id"],"pool-key")
            opts["pool_value"]=choose("Extractor pool template",h,["value"],"pool-value")
            opts["pool_evidence"]=choose("Pool evidence text (optional)",h,["where_in_text"],"pool-evidence",True)
        if kd_on:
            st.markdown("**Kd — one gold measurement per aptamer**")
            opts["gold_kd_value"]=choose("Gold Kd value",headers,["gold_kd_value"],"kd-gold")
            opts["gold_kd_unit"]=choose("Gold Kd unit",headers,["gold_kd_unit"],"kd-unit")
            opts["kd_sheet"]=st.selectbox("Extractor Kd worksheet",list(ei),index=list(ei).index("kd") if "kd" in ei else 0,key="kd-sheet")
            h=ei[opts["kd_sheet"]]["headers"]
            opts["kd_key"]=choose("Extractor Kd paper ID",h,["pk","paper_id"],"kd-key")
            opts["kd_value"]=choose("Extractor Kd structured values",h,["raw_values","value"],"kd-value")
        st.caption("Exact comparison after unit conversion; Kd tolerance is 5%. Uncertain identities need review.")
    return FieldConfig(pool_enabled=pool_on,kd_enabled=kd_on,**opts)


def field_review_path(data):
    return STORE/(data["run_id"]+"-fields-"+fields_fingerprint(data)[:12]+".json")


def field_review_panel(data, results, events):
    st.subheader("Review Pool / Kd")
    reviewer=st.text_input("Field reviewer identity",key="field-reviewer")
    targets=[(kind,row) for kind in ("pool","kd") for row in results[kind]["rows"]]
    remaining=[(kind,row) for kind,row in targets if row["status"]=="UNRESOLVED"]
    st.write(f"Unresolved field records: **{len(remaining)}** of {len(targets)}")
    show_all=st.checkbox("Show resolved records as well",value=False,key="field-review-all")
    visible=targets if show_all else remaining
    if not visible:
        st.success("All evaluated field records have an association or a missing decision.")
    else:
        records={row['gold']['id']:(kind,row) for kind,row in visible}
        def field_label(record_id):
            kind,row=records[record_id]
            return f"{kind.upper()} · {row['gold']['paper_id']} · {record_id}"
        record_id=st.selectbox("Gold field record",list(records),format_func=field_label,key="field-record")
        kind,row=records[record_id]
        g=row["gold"]
        st.json(json.loads(json.dumps({"gold":g,"linked":row["extractor"],"comparison":row["comparison"]},default=str)),expanded=False)
        options=[e for e in results[kind]["predictions"] if e["paper_id"]==g["paper_id"]]
        eid=st.selectbox("Prediction candidate",[""]+[e["id"] for e in options],
            format_func=lambda x: "None / missing" if not x else x+" · "+next(e["raw"] for e in options if e["id"]==x)[:50],
            key="field-candidate-"+g["id"])
        if eid:
            chosen=next(e for e in options if e["id"]==eid)
            st.json(json.loads(json.dumps(chosen,default=str)),expanded=False)
        cols=st.columns(4)
        for col,label,action in zip(cols,["Confirm identity","Reject pair","Mark missing","Leave unresolved"],
                                     ["confirm","reject","missing","unresolved"]):
            disabled=not reviewer.strip() or (action in ("confirm","reject") and not eid)
            if col.button(label,key="field-"+action,disabled=disabled):
                try:
                    new_events,_=append_field_review(data,events,action,reviewer,kind,g["id"],eid)
                    save_field_review(data,new_events,field_review_path(data),len(events))
                    st.session_state["field-review-events"]=new_events
                    st.session_state["flash"]=f"Pool/Kd review revision {len(new_events)} saved locally."
                    st.rerun()
                except ValueError as exc:st.error(str(exc))
    if events and st.button("Undo latest field review",disabled=not reviewer.strip()):
        try:
            new_events,_=append_field_review(data,events,"UNDO_LAST",reviewer)
            save_field_review(data,new_events,field_review_path(data),len(events))
            st.session_state["field-review-events"]=new_events
            st.session_state["flash"]=f"Pool/Kd review revision {len(new_events)} saved locally."
            st.rerun()
        except ValueError as exc:st.error(str(exc))


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
        unresolved=[g for g in paper.gold_ids if g not in am and g not in missing]
        only_unresolved=st.checkbox('Show unresolved golds first',value=True,key='only-unresolved')
        choices=unresolved+[g for g in paper.gold_ids if g not in unresolved] if only_unresolved else list(paper.gold_ids)
        # Keep the currently inspected record across review-driven reordering.
        # The toggle prioritizes unresolved golds; it must not hide accepted ones.
        widget_key=f'gold-{pid}'
        selection_key=f'selected-gold-{run.run_id}-{pid}'
        def remember_gold():st.session_state[selection_key]=st.session_state[widget_key]
        if choices:
            selected=st.session_state.get(selection_key,choices[0])
            st.session_state[selection_key]=selected if selected in choices else choices[0]
            st.session_state[widget_key]=st.session_state[selection_key]
            gid=st.selectbox('Gold record',choices,format_func=lambda g:f'{g} · {gm[g].name} · {len(gm[g].sequence.canonical)} nt',key=widget_key,on_change=remember_gold)
        else:gid=None
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


def _main():
    st.set_page_config(page_title='AptaBench Lite',layout='wide')
    st.title('AptaBench Lite');st.caption('Significant-reference evaluation · Sequence, optional Pool/Kd · Live manual review')
    with st.expander('Privacy and scientific scope'):
        st.write('Evaluation runs locally without external APIs. Do not expose this server publicly. Only significant gold references are scored. Pool/Kd are optional, conservative field evaluations, not biological identity guarantees.')
    st.subheader('Upload & configure')
    st.caption('Sequence evaluation always runs. Pool and Kd are optional, independent fields.')
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
        extra_cfg=configure_extra_fields(gb,eb,cfg.gold_sheet)
        gold,ext,attempted,diags=_preview(gb,eb,cfg.to_json())
        st.subheader('Input validation preview')
        st.write(f'{len(gold)} gold rows · {sum(g.significant for g in gold)} significant records · {sum(len(g.sequence.canonical or "") for g in gold if g.significant)} significant bases · {len(attempted)} linked attempted papers · {len(ext)} raw extractor items')
        st.dataframe([{'Paper':p,'Extractor items':sum(e.paper_id==p for e in ext)} for p in attempted],hide_index=True)
        if diags:
            with st.expander(f'Validation diagnostics ({len(diags)})',expanded=not attempted):st.dataframe([asdict(d) for d in diags],hide_index=True)
        if st.button('Run evaluation',type='primary',disabled=not attempted):
            with measured('run_evaluation'):
                with st.spinner('Evaluating fixed sequence associations…'):
                    run=_evaluate(gb,eb,cfg.to_json())
                with st.spinner('Loading optional Pool/Kd fields…'):
                    extra_data=_load_fields(gb,eb,run.run_id,extra_cfg.to_json(),run) if extra_cfg.pool_enabled or extra_cfg.kd_enabled else None
                with st.spinner('Restoring saved review decisions…'):
                    with measured('review_state_restore'):
                        path=STORE/(run.run_id+'.json')
                        value=import_review(run,path.read_bytes()) if path.exists() else run
                        if extra_data:
                            path=field_review_path(extra_data)
                            field_events=field_review_from_bytes(extra_data,path.read_bytes()) if path.exists() else []
                        else:field_events=[]
                # Publish one complete transaction after every stage succeeds.
                st.session_state['value']=value
                st.session_state['field-data']=extra_data
                st.session_state['field-review-events']=field_events
                st.session_state['input-key']=(gb,eb,cfg.to_json(),extra_cfg.to_json())
    except (ValueError,OSError) as exc:st.error(str(exc));return
    if 'value' not in st.session_state:return
    if st.session_state.get('input-key')!=(gb,eb,cfg.to_json(),extra_cfg.to_json()):
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
    with st.expander('Why are some gold records unresolved? (diagnostics)'):
        diagnostic = review_diagnostics(value)
        st.caption(diagnostic['interpretation'])
        st.write(f"{diagnostic['unresolved_gold']} significant gold records still need an identity decision.")
        if diagnostic['reason_counts']:
            st.dataframe(
                [{'Reason': key, 'Unresolved gold records': count}
                 for key, count in diagnostic['reason_counts']],
                hide_index=True,
            )
        else:
            st.info('No pending eligible significant golds in attempted papers.')
        st.caption('This is an abstention analysis, not an ablation or an estimated accuracy improvement.')
    paper_detail(value,sc,pop,tol)
    extra_data=st.session_state.get('field-data')
    if extra_data is not None:
        st.header("Pool & Kd results")
        if extra_data["warnings"]:
            with st.expander("Pool/Kd input diagnostics"):
                st.dataframe(extra_data["warnings"],hide_index=True)
        events=st.session_state.get('field-review-events',[])
        field_scores=replay_field_review(extra_data,events)
        for kind in ("pool","kd"):
            if not (extra_cfg.pool_enabled if kind=="pool" else extra_cfg.kd_enabled):continue
            fs=field_scores[kind]
            st.subheader(kind.upper())
            columns=st.columns(4)
            for col,key in zip(columns,("G","M","T","pending")):col.metric(key,fs[key])
            st.caption(fs["scope_warning"])
            st.dataframe([{"paper":v["gold"]["paper_id"],"gold_id":v["gold"]["id"],
                           "extractor_id":v["extractor"]["id"] if v["extractor"] else "",
                           "status":v["status"],"exact":v["comparison"].get("exact",False),
                           "tolerant":v["comparison"].get("tolerant",False),
                           "relative_error_pct":v["comparison"].get("relative_error_pct")}
                          for v in fs["rows"]],hide_index=True)
        field_review_panel(extra_data,field_scores,events)
        st.download_button("Download Pool/Kd review backup",field_review_to_bytes(extra_data,events),
                           "aptabench-field-review.json",mime="application/json")
        with st.expander("Restore Pool/Kd review backup"):
            upload=st.file_uploader("Restore field review-state JSON",type=["json"],key="field-review-upload")
            if upload and st.button("Restore field review"):
                try:
                    restored=field_review_from_bytes(extra_data,upload.getvalue())
                    if restored[:len(events)]!=events:
                        raise ValueError("Imported review history conflicts with locally saved history")
                    save_field_review(extra_data,restored,field_review_path(extra_data),len(events))
                    st.session_state["field-review-events"]=restored
                    st.rerun()
                except ValueError as exc:st.error(str(exc))
    st.header('Download report & resume')
    st.caption('Every committed action is autosaved under .local/reviews. Download a portable review backup before moving machines. Re-upload the identical inputs and mappings to resume.')
    include_report = st.checkbox('Include downloadable Excel report', value=True, key='include-report')
    if include_report:
        st.caption('One workbook, three focused tabs. Select which tabs to include. Default: all three.')
        report_options = ['Simple Summary', 'Debug Log', 'Logistics']
        report_sheets = st.multiselect(
            'Worksheets', report_options, default=report_options, key='report-sheets'
        )
        st.caption('The download goes to the browser default folder, or a location your browser asks you to choose. This app cannot specify a local client-side folder.')
    try:
        if include_report and report_sheets:
            # Streamlit evaluates the download_button data argument on every
            # rerun. Preparing an expensive report only on explicit request
            # avoids rebuilding all nucleotide-rich Excel rows while reviewing.
            from hashlib import sha256
            review_events = value.events if isinstance(value, ReviewedRun) else ()
            field_events = st.session_state.get('field-review-events', [])
            report_identity = sha256(repr((
                run.run_id, review_events, field_events, metrics['population'],
                metrics['tolerance'], metrics['sequence_scope'], tuple(report_sheets),
                fields_fingerprint(extra_data) if extra_data is not None else None,
            )).encode()).hexdigest()
            if st.button('Prepare Excel report', key='prepare-xlsx'):
                with st.spinner('Preparing the selected report once…'):
                    st.session_state['prepared-xlsx'] = (
                        report_identity,
                        export_workbook(
                            value, metrics, sheets=report_sheets,
                            field_data=extra_data, field_events=field_events,
                        ),
                    )
            prepared = st.session_state.get('prepared-xlsx')
            if prepared and prepared[0] == report_identity:
                st.download_button(
                    'Download Excel report', prepared[1],
                    'aptabench-evaluation.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    key='download-xlsx',
                )
            else:
                st.caption('Prepare the report after finishing review; changes to review decisions or settings require a fresh report.')
        st.download_button('Download JSON audit',export_audit(value,metrics,field_data=extra_data,field_events=st.session_state.get('field-review-events',[])),'aptabench-audit.json',mime='application/json',key='download-audit')
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



def main():
    trace=os.environ.get('APTABENCH_PERFORMANCE_LOG')
    if not trace:
        return _main()
    capture=Capture()
    start=perf_counter()
    completed=False
    try:
        with capture.activate():
            _main()
        completed=True
    finally:
        # Disabled by default. The opt-in trace stores timings/counts ONLY,
        # never widget values, source strings, paths from uploads, or records.
        total=perf_counter()-start
        excluded=sum(capture.stages.get(k,{}).get('seconds',0) for k in ('run_evaluation','excel_export'))
        result={'script_total_s':total,'render_excluding_run_export_s':max(0,total-excluded),
                'stages':capture.stages,'has_run': 'value' in st.session_state,'completed':completed,
                'field_review_revision':len(st.session_state.get('field-review-events',[])),
                'sequence_review_revision':len(getattr(st.session_state.get('value'),'events',()))}
        st.session_state['_performance']=result
        trace=os.environ.get('APTABENCH_PERFORMANCE_LOG')
        if trace:
            destination=Path(trace)
            destination.parent.mkdir(parents=True,exist_ok=True)
            with destination.open('a',encoding='utf-8') as stream:
                stream.write(json.dumps(result,sort_keys=True)+'\n')
