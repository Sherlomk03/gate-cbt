#!/usr/bin/env python3
"""Probe official GATE paper sources (2010-2021) and update a transparent source catalog.

This stage checks PDF availability, not per-question grading. It NEVER labels a
paper as CBT-ready or invents missing answer keys. Running this action does not
alter previously published daily exams or their local-browser attempts.
"""
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import requests
import fitz
from zoneinfo import ZoneInfo

PATH=pathlib.Path("pyq/historical/source-catalog-2010-2026.json")
HEADERS={"User-Agent":"Mozilla/5.0 (academic GATE PYQ source validation)"}
def fetch_pdf(url):
    for attempt in range(2):
        try:
            resp=requests.get(url,headers=HEADERS,timeout=(15,50))
            resp.raise_for_status()
            if not resp.content.startswith(b"%PDF"):
                raise ValueError(f"Not PDF: content-type {resp.headers.get('Content-Type')}")
            doc=fitz.open(stream=resp.content,filetype="pdf")
            pages=len(doc)
            if pages<2:raise ValueError("PDF too short")
            first=" ".join(doc[i].get_text("text") for i in range(min(3,pages)))
            doc.close()
            return {"verified":True,"url":url,"pages":pages,
                    "sha256":hashlib.sha256(resp.content).hexdigest(),
                    "textExtractable":len(first.strip())>60}
        except Exception as exc:
            err=f"{type(exc).__name__}: {str(exc)[:180]}"
    return {"verified":False,"reason":err}

def check(entry):
    id=entry["id"]
    url=entry.get("paperUrl") or entry.get("paperUrlCandidate")
    if not url:return id,{"verified":False,"reason":"No candidate URL"}
    return id,fetch_pdf(url)

def main():
    cat=json.loads(PATH.read_text(encoding="utf-8"))
    work=[x for x in cat["papers"] if x["year"]<=2021]
    results={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for id,result in pool.map(check,work):
            results[id]=result
            print("CHECK",id,"OK" if result["verified"] else result["reason"],flush=True)
    now=datetime.datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")
    for entry in work:
        result=results[entry["id"]]
        entry["lastProbeIST"]=now
        if result["verified"]:
            entry["paperUrl"]=result["url"]
            entry.pop("paperUrlCandidate",None)
            entry["sourceStatus"]="official_pdf_http_and_format_verified"
            entry["pdfPages"]=result["pages"]
            entry["pdfSha256"]=result["sha256"]
            entry["textExtractable"]=result["textExtractable"]
            entry.pop("lastProbeError",None)
        else:
            # Preserve any previous URL already independently verified.
            entry["lastProbeError"]=result["reason"]
    cat["lastArchiveProbeIST"]=now
    cat["archiveProbeSummary"]={
        "totalChecked":len(work),
        "verifiedPdf":sum(bool(results[x["id"]]["verified"]) for x in work),
        "unresolved":sum(not results[x["id"]]["verified"] for x in work)
    }
    # Deliberately unchanged CBT status: per-question images and official
    # keys are still required before question selection.
    PATH.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("DONE",cat["archiveProbeSummary"],flush=True)

if __name__=="__main__":main()
