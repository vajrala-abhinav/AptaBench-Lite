from dataclasses import dataclass, asdict
import json
from pathlib import PurePosixPath


@dataclass(frozen=True)
class RunConfig:
    gold_sheet: str = "Sheet1"
    extractor_sheet: str = "aptamer_seq"
    gold_paper: str = "paper_id"
    gold_key: str = "pdf_name"
    gold_id: str = "record_id"
    gold_sequence: str = "gold_sequence"
    gold_name: str = "aptamer_label_optional"
    gold_type: str = "aptamer_type"
    gold_status: str = "sequence_status"
    significant_values: tuple[str,...] = ("significant_sequence",)
    nonsignificant_values: tuple[str,...] = ("non_significant_sequence",)
    present_values: tuple[str,...] = ("present",)
    extractor_key: str = "pk"
    extractor_value: str = "value"
    extractor_name: str = ""
    extractor_notes: str = ""
    parser: str = "structured"
    sequence_key: str = "sequence"
    name_keys: tuple[str,...] = ("name", "aptamer_name")
    attempted_keys: tuple[str,...] = ()
    artifact_suffixes: tuple[str,...] = ()
    gold_filename: str = "gold.xlsx"
    extractor_filename: str = "extractor.xlsx"

    def __post_init__(self):
        for field in ('significant_values','nonsignificant_values','present_values','name_keys','attempted_keys','artifact_suffixes'):
            values=getattr(self,field)
            if not isinstance(values,(tuple,list)) or any(not isinstance(v,str) for v in values):raise ValueError(f'{field} must be an array of strings')
            object.__setattr__(self,field,tuple(values))
        for key,value in asdict(self).items():
            if not isinstance(value,tuple) and not isinstance(value,str):raise ValueError(f'{key} must be text')
        for key in ('gold_sheet','extractor_sheet','gold_paper','gold_key','gold_id','gold_sequence','gold_status','extractor_key','extractor_value','sequence_key'):
            if not getattr(self,key):raise ValueError(f'{key} is required')
        for field in ('gold_filename','extractor_filename'):
            object.__setattr__(self,field,PurePosixPath(getattr(self,field).replace('\\','/')).name)
        if self.parser not in ('structured','simple'):raise ValueError('Parser must be structured or simple')
        if not self.significant_values:raise ValueError('Explicit significant labels required')
        if set(self.significant_values)&set(self.nonsignificant_values):raise ValueError('Status labels overlap')

    def to_json(self):return json.dumps(asdict(self),sort_keys=True,ensure_ascii=False)
