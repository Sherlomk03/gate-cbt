#!/usr/bin/env python3
"""Stage official 2019-2021 EE/EC paper page images and source key inventories.

This is an *audit staging area*, NOT a CBT question importer:
- page images preserve figures even when a paper has no extractable text
- key rows are extracted if possible, but the row-to-question crop is not verified
- no question is marked selection-eligible and no daily CBT is changed
"""
from __future__ import annotations
import hashlib
import io
import json
import pathlib
import re
import time
from collections import Counter
import requests
import fitz
import pdfplumber
from PIL import Image

CAT=pathlib.Path("pyq/historical/source-catalog-2010-2026.json")
DEST=pathlib.Path("pyq/historical/staging")
PAGES=pathlib.Path("pyq/historical/source-pages")
SESSION=requests.Session()
SESSION.headers.update({"User-Agent":"Mozilla/5.0 (GATE source archive scholarly use)"})

def fetch(url):
    error=None
    for trial in range(3):
        try:
            response=SESSION.get(url,timeout=(15,60))
            response.raise_for_status()
            if not response.content.startswith(b"%PDF"):
                raise ValueError("Not a PDF response")
            return response.content
        except Exception as exc:
            error=exc
            time.sleep(trial+1)
    raise RuntimeError(f"Cannot fetch official PDF {url}: {error}")

def compact(text):
    return " ".join((text or "").replace("\n"," ").split()).strip()

def parse_key_rows(raw,branch):
    records={}
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables(table_settings={
                "vertical_strategy":"lines","horizontal_strategy":"lines"
            }) or []:
                for row in table:
                    cells=[compact(c) for c in row if compact(c)]
                    if len(cells)<5:continue
                    if not re.fullmatch(r"\d{1,2}",cells[0]):continue
                    n=int(cells[0])
                    try:idx=next(i for i,c in enumerate(cells) if c in ("MCQ","MSQ","NAT"))
                    except StopIteration:continue
                    if idx+3>=len(cells):continue
                    kind,section,key,marks=cells[idx:idx+4]
                    if section not in ("GA",branch) or marks not in ("1","2") or not key:continue
                    if not ((section=="GA" and 1<=n<=10) or (section==branch and 1<=n<=55)):continue
                    record={"number":n,"section":section,"type":kind,
                            "marks":int(marks),"officialKeyAsPrinted":key}
                    records[(section,n)]=record
    out=sorted(records.values(),key=lambda q:(q["section"]!="GA",q["number"]))
    sections=Counter(q["section"] for q in out)
    return out,sections.get("GA",0)==10 and sections.get(branch,0)==55

def stage(entry):
    year,branch=entry["year"],entry["branch"]
    source_id=entry["id"]
    old=DEST/(source_id+".json")
    if old.exists():
        obj=json.loads(old.read_text())
        print("ALREADY STAGED",source_id,flush=True)
        return obj
    pdf=fetch(entry["paperUrl"])
    doc=fitz.open(stream=pdf,filetype="pdf")
    dst=PAGES/source_id
    dst.mkdir(parents=True,exist_ok=True)
    pages=[]
    for i,page in enumerate(doc):
        path=dst/(f"p{i+1:03d}.webp")
        pix=page.get_pixmap(matrix=fitz.Matrix(1.3,1.3),alpha=False,colorspace=fitz.csRGB)
        picture=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
        picture.save(path,format="WEBP",quality=68,method=4)
        pages.append(str(path.relative_to(pathlib.Path("."))))
    pageCount=len(doc)
    doc.close()
    key_pdf=fetch(entry["keyUrl"]) if entry.get("keyUrl") else pdf
    key_rows,keys_complete=parse_key_rows(key_pdf,branch)
    report={
        "year":year,"branch":branch,"sourceId":source_id,
        "sourcePaperUrl":entry["paperUrl"],"sourcePaperSha256":hashlib.sha256(pdf).hexdigest(),
        "sourcePages":pages,"sourcePageCount":pageCount,
        "officialKeyUrl":entry.get("keyUrl") or entry["paperUrl"],
        "officialKeySha256":hashlib.sha256(key_pdf).hexdigest(),
        "extractedKeyRows":key_rows,
        "keyRowsComplete":keys_complete,
        "keyStatus":"table_rows_extracted_needs_number_session_mapping" if keys_complete else "partial_key_needs_manual_review",
        "cbtStatus":"staged_original_pages_not_question_crops",
        "selectionEligible":False,
        "subjectTagsReviewStatus":"not_reviewed",
        "notes":"Source page images retain original diagrams and options. Before daily selection, split into exact question crops, verify each source/question number and key, audit syllabus tags. Never infer missing keys."
    }
    old.parent.mkdir(parents=True,exist_ok=True)
    old.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("STAGED",source_id,pageCount,"pages",len(key_rows),"key entries",flush=True)
    return report

def main():
    obj=json.loads(CAT.read_text())
    target=[x for x in obj["papers"] if x["year"] in (2019,2020,2021) and x["branch"] in ("EC","EE") and x.get("paperUrl")]
    if len(target)!=6:
        raise RuntimeError(f"Expected six official sources, got {len(target)}")
    reports=[]
    for entry in target:
        reports.append(stage(entry))
    index={
      "schemaVersion":1,"sourceYears":[2019,2020,2021],
      "readyForCBT":False,"sourceSessionsNeedAudit":True,
      "reports":[{"id":r["sourceId"],"file":r["sourceId"]+".json",
                  "sourcePageCount":r["sourcePageCount"],
                  "extractedKeyRowCount":len(r["extractedKeyRows"]),
                  "keyRowsComplete":r["keyRowsComplete"],
                  "eligibleForDaily":False} for r in reports],
      "description":"Authentic PDF page images and extracted key inventory only; no question-level verification yet."
    }
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/"index.json").write_text(json.dumps(index,indent=2)+"\n")
    print("STAGING READY",len(reports),"papers; no papers were added to CBT eligibility",flush=True)

if __name__=="__main__":
    main()
