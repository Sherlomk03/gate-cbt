#!/usr/bin/env python3
"""OCR *staging* of scanned official GATE 2019/2021 answer key images.

These original scans lack an extractable text layer. OCR rows remain provisional,
even when plausible; raw source page images are retained and MUST be manually
checked before any question is eligible for CBT grading.
"""
import json,pathlib,re
from collections import defaultdict
from PIL import Image,ImageOps,ImageEnhance
import pytesseract

ROOT=pathlib.Path("pyq/historical")
OUT=ROOT/"key-ocr"
TARGETS={
 "2019-EC":[ROOT/"source-pages/2019-EC"/f"p{n:03d}.webp" for n in (29,30,31)],
 "2019-EE":[ROOT/"source-pages/2019-EE"/f"p{n:03d}.webp" for n in (14,15,16)],
 "2021-EC":sorted((ROOT/"key-pages/2021-EC").glob("p*.webp")),
 "2021-EE":sorted((ROOT/"key-pages/2021-EE").glob("p*.webp")),
}
def parse(lines,branch,year):
 rows={};unparsed=[]
 for line in lines:
    line=" ".join(line.split())
    if not re.match(r"^\d{1,2}\s",line):continue
    # OCR may split a negative NAT range into several whitespace tokens.
    pattern2021=rf'^(\d{{1,2}})\s+(\d)\s+(MCQ|MSQ|NAT)\s+(GA|{branch})\s+(.+?)\s+([12])\s+(?:0|1/3|2/3)\s*$'
    pattern2019=rf'^(\d{{1,2}})\s+(MCQ|MSQ|NAT)\s+(GA|{branch})\s+(.+?)\s+([12])\s*$'
    m=re.match(pattern2021 if year==2021 else pattern2019,line,re.I)
    if not m:
        unparsed.append(line)
        continue
    if year==2021:
        n,session,kind,section,key,marks=m.groups()
    else:
        n,kind,section,key,marks=m.groups()
        session=None
    n=int(n)
    if n<1 or n>(10 if section=="GA" else 55):continue
    if section not in ("GA",branch):continue
    id=(section,n)
    rows[id]={"section":section,"number":n,"session":int(session) if session else None,
              "type":kind.upper(),"keyCandidateOCR":key,"marks":int(marks),
              "ocrVerified":False}
 return sorted(rows.values(),key=lambda r:(r["section"]!="GA",r["number"])),unparsed
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 index=[]
 for name,paths in TARGETS.items():
    year,branch=int(name[:4]),name[-2:]
    if not paths or any(not p.exists() for p in paths):
        raise RuntimeError(f"Source key-page scans missing for {name}: {paths}")
    all_lines=[];pages=[]
    for p in paths:
        im=Image.open(p).convert("RGB")
        # Scan native page just once; no invented text or replacement questions.
        ocr=pytesseract.image_to_string(im,config="--psm 6",lang="eng")
        pages.append({"file":str(p),"ocrText":ocr})
        all_lines+=ocr.splitlines()
    rows,unparsed=parse(all_lines,branch,year)
    report={"id":name,"status":"scanned_key_ocr_needs_visual_verification",
            "keySourcePages":[str(p) for p in paths],
            "recognizedRows":rows,"recognizedCount":len(rows),
            "unparsedCandidateLines":unparsed,"sourcePageOCR":pages,
            "complete":len(rows)==65 and sum(q["section"]=="GA" for q in rows)==10 and sum(q["section"]==branch for q in rows)==55,
            "cbtEligible":False}
    (OUT/(name+".json")).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("OCR",name,len(rows),"candidate key rows",len(unparsed),"unparsed; complete",report["complete"],flush=True)
    index.append({"id":name,"recognizedCount":len(rows),"complete":report["complete"],"readyForCBT":False})
 (OUT/"index.json").write_text(json.dumps({"reports":index,"status":"provisional_key_ocr_not_usable_for_grading"},indent=2)+"\n")
if __name__=="__main__":main()
