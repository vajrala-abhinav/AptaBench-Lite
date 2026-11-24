"""Generate only synthetic, redistributable examples."""
from pathlib import Path
from openpyxl import Workbook
import json


def make_examples(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    gold=Workbook();w=gold.active;w.title='Sheet1'
    w.append(['paper_id','pdf_name','record_id','gold_sequence','aptamer_label_optional','aptamer_type','sequence_status'])
    for row in [
        ['DEMO1','demo-one.pdf','G1','ACGTCAGT','Apt-1','significant_sequence','present'],
        ['DEMO1','demo-one.pdf','G2','TGCACGTA','Apt-2','significant_sequence','present'],
        ['DEMO2','demo-two.pdf','G3','CGTAGTCA','Apt-3','significant_sequence','present'],
        ['DEMO2','demo-two.pdf','G4','GACTCGAT','Apt-4','significant_sequence','present'],
        ['DEMO2','demo-two.pdf','G5','CCCCGGGG','context-only','non_significant_sequence','present'],
        ['DEMO3','demo-three.pdf','G6','AGGTCCTA','Apt-6','significant_sequence','present']]:w.append(row)
    gold.save(directory/'gold.xlsx')
    ext=Workbook();w=ext.active;w.title='aptamer_seq';w.append(['pk','value'])
    w.append(['demo-one',json.dumps([{'sequence':'acgt cagt','name':'Apt-1'},{'sequence':'TTTGCACGTAGG','name':'Apt-2'},{'sequence':'ACGTCAGT','name':'Apt-1'}])])
    w.append(['demo-two',json.dumps([{'sequence':'CGTAGTCA','name':'Apt-3'},{'sequence':'AAAAAAAA','name':'Apt-4'},{'sequence':'CCCCGGGG'}])])
    w.append(['demo-three','[]']);ext.save(directory/'extractor.xlsx')


if __name__=='__main__':make_examples(Path(__file__).resolve().parents[1]/'examples')
