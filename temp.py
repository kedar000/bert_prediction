# from __future__ import annotations

# import argparse
# import json
# import zipfile
# import xml.etree.ElementTree as ET
# from dataclasses import dataclass
# from pathlib import Path
# from typing import Dict, Iterable, List, Optional, Tuple

# VALID_LABELS = {"mcq", "passage", "main", "subquestion"}


# def _parse_col_idx(col_letters: str) -> int:
#     col_letters = col_letters.strip().upper()
#     idx = 0
#     for ch in col_letters:
#         if not ("A" <= ch <= "Z"):
#             break
#         idx = idx * 26 + (ord(ch) - ord("A") + 1)
#     return idx - 1


# def _cell_ref_to_col_idx(cell_ref: str) -> Optional[int]:
#     col_letters = ""
#     for ch in cell_ref:
#         if ch.isalpha():
#             col_letters += ch
#         else:
#             break
#     if not col_letters:
#         return None
#     return _parse_col_idx(col_letters)


# def _get_namespaced_attr_id(attrib: Dict[str, str]) -> str:
#     for k, v in attrib.items():
#         if k.endswith("}id") or k.endswith(":id") or k == "id":
#             return v
#     return ""


# @dataclass
# class SheetSpec:
#     sheet_name: str
#     sheet_path: str


# def _open_xlsx_zip(xlsx_path: Path) -> zipfile.ZipFile:
#     return zipfile.ZipFile(xlsx_path)


# def _find_sheets(z: zipfile.ZipFile) -> List[SheetSpec]:
#     workbook_xml = z.read("xl/workbook.xml")
#     wb = ET.fromstring(workbook_xml)
#     wb_ns = {"x": wb.tag.split("}")[0].strip("{")}

#     sheets_el = wb.find("x:sheets", wb_ns)
#     if sheets_el is None:
#         raise RuntimeError("xl/workbook.xml missing x:sheets")

#     rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
#     rel_ns = {"x": rels.tag.split("}")[0].strip("{")}

#     id_to_target: Dict[str, str] = {}
#     for rel in rels.findall("x:Relationship", rel_ns):
#         rid = rel.attrib.get("Id")
#         target = rel.attrib.get("Target")
#         if rid and target:
#             id_to_target[rid] = target

#     out: List[SheetSpec] = []
#     for sh in sheets_el.findall("x:sheet", wb_ns):
#         name = sh.attrib.get("name", "")
#         rid = _get_namespaced_attr_id(sh.attrib)

#         if not rid or rid not in id_to_target:
#             continue

#         target = id_to_target[rid].replace("\\", "/")

#         # ✅ FIX: avoid duplicating "xl/"
#         if target.startswith("xl/"):
#             sheet_path = target
#         else:
#             sheet_path = "xl/" + target

#         out.append(SheetSpec(sheet_name=name, sheet_path=sheet_path))

#     if not out:
#         raise RuntimeError("No sheets found in workbook.")

#     return out


# def _load_shared_strings(z: zipfile.ZipFile) -> List[str]:
#     if "xl/sharedStrings.xml" not in z.namelist():
#         return []

#     ss = ET.fromstring(z.read("xl/sharedStrings.xml"))
#     ss_ns = {"x": ss.tag.split("}")[0].strip("{")}

#     shared: List[str] = []
#     for si in ss.findall("x:si", ss_ns):
#         t = si.find(".//x:t", ss_ns)
#         shared.append(t.text if t is not None and t.text is not None else "")

#     return shared


# def _read_sheet_rows(z: zipfile.ZipFile, sheet_path: str) -> Iterable[Tuple[int, Dict[int, str]]]:
#     sheet_xml = z.read(sheet_path)
#     root = ET.fromstring(sheet_xml)
#     sheet_ns = {"x": root.tag.split("}")[0].strip("{")}

#     shared_strings = _load_shared_strings(z)

#     for row in root.findall(".//x:sheetData/x:row", sheet_ns):
#         r_idx = int(row.attrib.get("r", "0"))
#         cells: Dict[int, str] = {}

#         for c in row.findall("x:c", sheet_ns):
#             r_addr = c.attrib.get("r", "")
#             col_idx = _cell_ref_to_col_idx(r_addr)
#             if col_idx is None:
#                 continue

#             t = c.attrib.get("t", "")
#             val_node = c.find("x:v", sheet_ns)

#             if t == "s":
#                 if val_node is None or val_node.text is None:
#                     continue
#                 si = int(val_node.text)
#                 cells[col_idx] = shared_strings[si] if 0 <= si < len(shared_strings) else ""

#             elif t == "inlineStr":
#                 tnode = c.find(".//x:is/x:t", sheet_ns)
#                 cells[col_idx] = tnode.text if tnode is not None and tnode.text is not None else ""

#             else:
#                 if val_node is None or val_node.text is None:
#                     continue
#                 cells[col_idx] = val_node.text

#         yield r_idx, cells


# def normalize_label(raw: str) -> Optional[str]:
#     s = (raw or "").strip().lower()
#     if not s:
#         return None

#     s = s.replace(" ", "").replace("_", "")

#     if s in VALID_LABELS:
#         return s

#     if "mcq" in s:
#         return "mcq"
#     if "passage" in s:
#         return "passage"
#     if "main" in s:
#         return "main"
#     if "sub" in s:
#         return "subquestion"

#     return None


# def excel_to_jsonl(
#     xlsx_path: Path,
#     out_jsonl: Path,
#     *,
#     question_header: str = "question",
#     label_header: str = "label",
#     encoding: str = "utf-8",
# ) -> Dict[str, object]:

#     with _open_xlsx_zip(xlsx_path) as z:
#         sheets = _find_sheets(z)
#         sheet = sheets[0]

#         rows = list(_read_sheet_rows(z, sheet.sheet_path))
#         if not rows:
#             raise RuntimeError("No rows found.")

#         header_cells = {}
#         for r_idx, cells in rows:
#             if r_idx == 1:
#                 header_cells = cells
#                 break

#         q_col = None
#         l_col = None

#         for col_idx, val in header_cells.items():
#             hv = (val or "").strip().lower()
#             if hv == question_header:
#                 q_col = col_idx
#             if hv == label_header:
#                 l_col = col_idx

#         if q_col is None or l_col is None:
#             for col_idx, val in header_cells.items():
#                 hv = (val or "").strip().lower()
#                 if q_col is None and "question" in hv:
#                     q_col = col_idx
#                 if l_col is None and "label" in hv:
#                     l_col = col_idx

#         if q_col is None or l_col is None:
#             raise RuntimeError("Could not locate question/label columns.")

#         out_jsonl.parent.mkdir(parents=True, exist_ok=True)

#         unknown_labels = {}
#         kept = 0
#         total_data_rows = 0

#         with out_jsonl.open("w", encoding=encoding) as f:
#             for r_idx, cells in rows:
#                 if r_idx <= 1:
#                     continue

#                 total_data_rows += 1

#                 q = (cells.get(q_col) or "").strip()
#                 raw_l = (cells.get(l_col) or "").strip()

#                 if not q or not raw_l:
#                     continue

#                 norm_l = normalize_label(raw_l)  # ✅ fixed

#                 if norm_l is None:
#                     unknown_labels[raw_l] = unknown_labels.get(raw_l, 0) + 1
#                     continue

#                 f.write(json.dumps({"text": q, "label": norm_l}, ensure_ascii=False) + "\n")
#                 kept += 1

#     return {
#         "xlsx": str(xlsx_path),
#         "sheet": sheet.sheet_name,
#         "out_jsonl": str(out_jsonl),
#         "kept": kept,
#         "total_data_rows": total_data_rows,
#         "unknown_labels": unknown_labels,
#     }


# def main():
#     ap = argparse.ArgumentParser()
#     ap.add_argument("--input_train", required=True)
#     ap.add_argument("--input_val", required=True)
#     ap.add_argument("--out_train", default="data/train.jsonl")
#     ap.add_argument("--out_val", default="data/val.jsonl")

#     args = ap.parse_args()

#     stats_train = excel_to_jsonl(Path(args.input_train), Path(args.out_train))
#     stats_val = excel_to_jsonl(Path(args.input_val), Path(args.out_val))

#     print(json.dumps({"train": stats_train, "val": stats_val}, indent=2))


# if __name__ == "__main__":  # ✅ fixed
#     main()

from future import annotations

import argparse
import json
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

VALID_LABELS = {"mcq", "passage", "main", "subquestion"}

def _parse_col_idx(col_letters: str) -> int:
# "A" -> 0, "B" -> 1, ..., "AA" -> 26
col_letters = col_letters.strip().upper()
idx = 0
for ch in col_letters:
if not ("A" <= ch <= "Z"):
break
idx = idx * 26 + (ord(ch) - ord("A") + 1)
return idx - 1

def _cell_ref_to_col_idx(cell_ref: str) -> Optional[int]:
# cell_ref like "A1", "BC12"
col_letters = ""
for ch in cell_ref:
if ch.isalpha():
col_letters += ch
else:
break
if not col_letters:
return None
return _parse_col_idx(col_letters)

def _get_namespaced_attr_id(attrib: Dict[str, str]) -> str:
# In ElementTree, r:id may show up as "{ns}id" or end with ":id"
for k, v in attrib.items():
if k.endswith("}id") or k.endswith(":id") or k == "id":
return v
return ""

@dataclass
class SheetSpec:
sheet_name: str
sheet_path: str  # inside zip, e.g. "xl/worksheets/sheet1.xml"

def _open_xlsx_zip(xlsx_path: Path) -> zipfile.ZipFile:
return zipfile.ZipFile(xlsx_path)

def _find_sheets(z: zipfile.ZipFile) -> List[SheetSpec]:
workbook_xml = z.read("xl/workbook.xml")
wb = ET.fromstring(workbook_xml)
wb_ns = {"x": wb.tag.split("}")[0].strip("{")}

sheets_el = wb.find("x:sheets", wb_ns)  
if sheets_el is None:  
    raise RuntimeError("xl/workbook.xml missing x:sheets")  

rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))  
rel_ns = {"x": rels.tag.split("}")[0].strip("{")}  
id_to_target: Dict[str, str] = {}  
for rel in rels.findall("x:Relationship", rel_ns):  
    rid = rel.attrib.get("Id")  
    target = rel.attrib.get("Target")  
    if rid and target:  
        id_to_target[rid] = target  

out: List[SheetSpec] = []  
for sh in sheets_el.findall("x:sheet", wb_ns):  
    name = sh.attrib.get("name", "")  
    rid = _get_namespaced_attr_id(sh.attrib)  
    if not rid or rid not in id_to_target:  
        continue  
    target = id_to_target[rid].replace("\\", "/")  
    out.append(SheetSpec(sheet_name=name, sheet_path="xl/" + target))  

if not out:  
    raise RuntimeError("No sheets found in workbook.")  
return out

def _load_shared_strings(z: zipfile.ZipFile) -> List[str]:
if "xl/sharedStrings.xml" not in z.namelist():
return []
ss = ET.fromstring(z.read("xl/sharedStrings.xml"))
ss_ns = {"x": ss.tag.split("}")[0].strip("{")}
shared: List[str] = []
for si in ss.findall("x:si", ss_ns):
# value can be in t nodes
t = si.find(".//x:t", ss_ns)
shared.append(t.text if t is not None and t.text is not None else "")
return shared

def _read_sheet_rows(z: zipfile.ZipFile, sheet_path: str) -> Iterable[Tuple[int, Dict[int, str]]]:
sheet_xml = z.read(sheet_path)
root = ET.fromstring(sheet_xml)
sheet_ns = {"x": root.tag.split("}")[0].strip("{")}

shared_strings = _load_shared_strings(z)  

# sheetData contains rows/cells  
for row in root.findall(".//x:sheetData/x:row", sheet_ns):  
    r_idx = int(row.attrib.get("r", "0"))  
    cells: Dict[int, str] = {}  
    for c in row.findall("x:c", sheet_ns):  
        r_addr = c.attrib.get("r", "")  
        col_idx = _cell_ref_to_col_idx(r_addr)  
        if col_idx is None:  
            continue  

        t = c.attrib.get("t", "")  
        val_node = c.find("x:v", sheet_ns)  
        if t == "s":  
            if val_node is None or val_node.text is None:  
                continue  
            si = int(val_node.text)  
            cells[col_idx] = shared_strings[si] if 0 <= si < len(shared_strings) else ""  
        elif t == "inlineStr":  
            # inline string in <is><t>...</t></is>  
            tnode = c.find(".//x:is/x:t", sheet_ns)  
            cells[col_idx] = tnode.text if tnode is not None and tnode.text is not None else ""  
        else:  
            if val_node is None or val_node.text is None:  
                continue  
            cells[col_idx] = val_node.text  

    yield r_idx, cells

def normalize_label(raw: str) -> Optional[str]:
s = (raw or "").strip().lower()
if not s:
return None
s = s.replace(" ", "").replace("", "")
if s in VALID_LABELS:
return s

# light heuristics for common variants  
if "mcq" in s:  
    return "mcq"  
if "passage" in s:  
    return "passage"  
if s in {"mainquestion", "mainq"} or "main" in s:  
    return "main"  
if "sub" in s:  
    return "subquestion"  
return None

def excel_to_jsonl(
xlsx_path: Path,
out_jsonl: Path,
*,
question_header: str = "question",
label_header: str = "label",
encoding: str = "utf-8",
) -> Dict[str, object]:
with _open_xlsx_zip(xlsx_path) as z:
sheets = _find_sheets(z)
# By default, use first sheet (matches inspect_xlsx.py behavior)
sheet = sheets[0]

rows = list(_read_sheet_rows(z, sheet.sheet_path))  
    if not rows:  
        raise RuntimeError("No rows found.")  

    # header row = first row with r==1  
    header_cells: Dict[int, str] = {}  
    header_row_num = None  
    for r_idx, cells in rows:  
        if r_idx == 1:  
            header_cells = cells  
            header_row_num = r_idx  
            break  
    if header_row_num != 1:  
        raise RuntimeError("Could not find header row (r=1).")  

    # Map column indexes based on header text  
    q_col = None  
    l_col = None  
    for col_idx, val in header_cells.items():  
        hv = (val or "").strip().lower()  
        if hv == question_header:  
            q_col = col_idx  
        if hv == label_header:  
            l_col = col_idx  
    if q_col is None or l_col is None:  
        # fallback: first column that contains 'question' and 'label'  
        for col_idx, val in header_cells.items():  
            hv = (val or "").strip().lower()  
            if q_col is None and "question" in hv:  
                q_col = col_idx  
            if l_col is None and "label" in hv:  
                l_col = col_idx  
    if q_col is None or l_col is None:  
        raise RuntimeError(f"Could not locate question/label columns in header: {header_cells}")  

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)  
    unknown_labels: Dict[str, int] = {}  
    kept = 0  
    total_data_rows = 0  

    with out_jsonl.open("w", encoding=encoding) as f:  
        for r_idx, cells in rows:  
            if r_idx <= 1:  
                continue  
            total_data_rows += 1  
            q = (cells.get(q_col) or "").strip()  
            raw_l = (cells.get(l_col) or "").strip()  
            if not q or not raw_l:  
                continue  
            norm_l = _normalize_label(raw_l)  
            if norm_l is None:  
                unknown_labels[raw_l] = unknown_labels.get(raw_l, 0) + 1  
                continue  
            f.write(json.dumps({"text": q, "label": norm_l}, ensure_ascii=False) + "\n")  
            kept += 1  

return {  
    "xlsx": str(xlsx_path),  
    "sheet": sheet.sheet_name,  
    "out_jsonl": str(out_jsonl),  
    "kept": kept,  
    "total_data_rows": total_data_rows,  
    "unknown_labels": unknown_labels,  
}

def main() -> None:
ap = argparse.ArgumentParser()
ap.add_argument("--input_train", required=True, help="Path to bert_dataset.xlsx")
ap.add_argument("--input_val", required=True, help="Path to test_2.xlsx")
ap.add_argument("--out_train", default="data/train.jsonl")
ap.add_argument("--out_val", default="data/val.jsonl")
ap.add_argument("--question_header", default="question")
ap.add_argument("--label_header", default="label")
args = ap.parse_args()

out_train = Path(args.out_train)  
out_val = Path(args.out_val)  

stats_train = excel_to_jsonl(  
    Path(args.input_train),  
    out_train,  
    question_header=args.question_header,  
    label_header=args.label_header,  
)  
stats_val = excel_to_jsonl(  
    Path(args.input_val),  
    out_val,  
    question_header=args.question_header,  
    label_header=args.label_header,  
)  

report = {"train": stats_train, "val": stats_val}  
print(json.dumps(report, ensure_ascii=False, indent=2))

if name == "main":
main()