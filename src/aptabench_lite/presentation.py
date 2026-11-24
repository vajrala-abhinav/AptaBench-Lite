"""Single color/operation mapping for HTML and Excel; never realigns."""
from html import escape
COLORS={'MATCH':'#B8E5C5','INSERTION':'#FFE69A','DELETION':'#FFE69A',
        'SUBSTITUTION':'#F5B5B5','FREE_EXTRACTOR_FLANK':'#D9DDE3'}


def alignment_html(trace):
    def row(label,text):
        spans=''.join(f'<span title="{op}" style="background:{COLORS[op]};color:#152536">{escape(c)}</span>'
                      for c,op in zip(text,trace.operations))
        return f'<div style="white-space:pre">{label:12}5′ {spans} 3′</div>'
    return ('<div style="overflow-x:auto;font-family:monospace;line-height:1.9;font-size:16px">'+
            row('Gold',trace.aligned_gold)+row('Extractor',trace.aligned_extractor)+'</div>')
