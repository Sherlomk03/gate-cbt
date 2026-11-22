#!/usr/bin/env python3
"""Publish a real-photo GATE PYQ 40-question daily CBT test.
Official source IDs and original screenshot paths are preserved.
Provisional taxonomy is disclosed; never pad with fabricated questions.
"""
from datetime import datetime,date,timedelta
from zoneinfo import ZoneInfo
import json,pathlib,hashlib,random,re,sys

ROOT=pathlib.Path("pyq/five-years")
OUT=pathlib.Path("papers/daily-pyq")
OUT.mkdir(parents=True,exist_ok=True)
START=date(2026,11,21)
PAIRS=[
 ("Analog Electronics","Digital Electronics"),
 ("Signals & Systems","Digital Electronics"),
 ("Analog Electronics","Electrical Machines"),
 ("Power Systems","Electrical Machines"),
 ("Power Electronics","Signals & Systems")
]
EXCLUDED={"Control Systems","Unclassified","Communication Systems","Electromagnetics","Microprocessors"}
REQUIRED=("Engineering Mathematics","Network Theory")

def get_questions():
    questions=[]
    for path in sorted(ROOT.glob("20??-??.json")):
        source=json.loads(path.read_text())
        for q in source["questions"]:
            if q["number"]<=10:continue
            if q.get("subject") in EXCLUDED:continue
            # Never select questions whose source-based category was not approved.
            if q.get("selectionEligible") is not True:continue
            lead=(q.get("sourceExtract") or "")[:480].lower()
            if q["subject"]=="Engineering Mathematics" and re.search(r"standing wave ratio|economic dispatch|generator buses|nominal.π model|nominal.pi model|transmission line|\bpower system\b|\bpower network\b|\bthevenin\b|\bload flow\b",lead):continue
            if not q.get("imagePath") or not q.get("officialKey"):continue
            if q["type"] not in ("MCQ","MSQ","NAT"):continue
            questions.append({
              "id":q["id"],"sourceId":f'GATE {source["year"]} {source["branch"]} Q{q["number"]}',
              "year":source["year"],"branch":source["branch"],"questionNumber":q["number"],
              "subject":q.get("subject") or "Unclassified","topic":q.get("topic","Needs review"),
              "classificationStatus":q.get("classificationStatus","unclassified"),
              "taxonomyReviewStatus":q.get("taxonomyReviewStatus","requires_visual_review"),
              "selectionEligibleForFuture":True,
              "classificationMethod":q.get("classificationMethod","source-linked classification"),
              "sourceExcerpt":(q.get("sourceExtract") or "")[:220],
              "type":q["type"],"marks":q["marks"],"officialKey":q["officialKey"],
              "imagePath":"./pyq/five-years/"+q["imagePath"],
              "paperUrl":source["paperUrl"],"keyUrl":source["keyUrl"],
              "pdfPage":q.get("imageStartPage") or q.get("pdfPage"),
              "imageAuditStatus":q.get("imageAuditStatus","automated_crop")
            })
    return questions


def get_ace_signals():
    """Supplement Signals block with user-provided ACE classroom questions.
    A classroom question is NEVER labeled as an official GATE PYQ.
    Exclude missing keys or ambiguous questions; preserve explanatory diagram descriptions.
    """
    source=json.loads(pathlib.Path("practice/ace-signals-2022.json").read_text())
    allowed={1,2,3,4,5,6,8,9,10,11,12,13,14,15,16,17,18}
    output=[]
    for q in source["questions"]:
        if q["number"] not in allowed or q["answer"] is None:
            continue
        output.append({
          "id":q["id"],"sourceId":f'ACE 2022 Signals & Systems Q{q["number"]}',
          "year":2022,"branch":"ACE EEE","questionNumber":q["number"],
          "subject":"Signals & Systems","topic":q["topic"],
          "classificationStatus":"user_supplied_classroom_test",
          "sourceType":"ace_classroom","officialGatePYQ":False,
          "answerStatus":q["answerStatus"],
          "type":q["type"],"marks":q["marks"],"officialKey":",".join(q["answer"]) if isinstance(q["answer"],list) else str(q["answer"]),
          "stem":q["stem"],"options":q.get("options",[]),
          "imagePath":None,"paperUrl":None,"keyUrl":None,
          "pdfPage":q["sourcePages"],
          "sourceNote":"ACE Engineering Academy 2022 classroom test photographed by user; individually solved key, not official GATE answer key."
        })
    return output

def deterministic_sort(questions,day,seed):
    return sorted(questions,key=lambda q:hashlib.sha256(f'{seed}-{day.isoformat()}-{q["id"]}'.encode()).hexdigest())

def choose(items, subject, today,used,history):
    candidates=[q for q in items if q["subject"]==subject]
    distinct=[q for q in candidates if q["id"] not in used]
    selected=[]
    if subject=="Signals & Systems":
        # Six actual GATE PYQs + four explicitly labeled ACE classroom problems.
        # Prefer unseen for both sources; fall back transparently if exhausted.
        pools=[
            ([q for q in candidates if q.get("sourceType")=="ace_classroom"],4),
            ([q for q in candidates if q.get("sourceType")!="ace_classroom"],6)
        ]
    else:
        pools=[(candidates,10)]
    for pool,limit in pools:
        start=len(selected)
        for q in deterministic_sort([x for x in pool if x["id"] not in used],today,subject+"fresh"):
            if len(selected)-start>=limit:break
            if q["id"] not in {x["id"] for x in selected}:selected.append(q)
        for q in deterministic_sort([x for x in pool if x["id"] in used],today,subject+"repeat"):
            if len(selected)-start>=limit:break
            if q["id"] not in {x["id"] for x in selected}:selected.append(q)
    # Avoid failing a daily paper if fewer than 4 ACE problems are eligible.
    if len(selected)<10:
        for q in deterministic_sort(candidates,today,subject+"remaining"):
            if len(selected)==10:break
            if q["id"] not in {x["id"] for x in selected}:selected.append(q)
    return selected,len(distinct),len(candidates)

def day_subjects(allq,today):
    base=(today-START).days
    pair=PAIRS[base%len(PAIRS)]
    counts={s:sum(q["subject"]==s for q in allq) for s in set(q["subject"] for q in allq)}
    if all(counts.get(s,0)>=10 for s in pair):
        return list(REQUIRED)+list(pair),None
    backups=["Analog Electronics","Digital Electronics","Signals & Systems","Electrical Machines","Power Electronics","Power Systems"]
    rotation=[s for s in backups if counts.get(s,0)>=10]
    if len(rotation)<2:raise RuntimeError("Insufficient pool for two rotating technical subjects")
    a=rotation[(base*2)%len(rotation)]
    b=next(x for x in rotation[(base*2+1)%len(rotation):]+rotation[:(base*2+1)%len(rotation)] if x!=a)
    return list(REQUIRED)+[a,b],f'Requested pair {pair} is too small in current classified bank; used {a}, {b} as verified-source substitutes.'

def main():
    bank=get_questions()+get_ace_signals()
    existing=[]
    for path in sorted(OUT.glob("20??-??-??.json")):
        try:
            p=json.loads(path.read_text())
            if isinstance(p.get("questions"),list):existing.append(p)
        except Exception:pass
    ist=datetime.now(ZoneInfo("Asia/Kolkata")).date()
    target=START if ist<START else ist
    if len(sys.argv)>1:target=date.fromisoformat(sys.argv[1])
    dest=OUT/f'{target.isoformat()}.json'
    if dest.exists():
        print("Daily paper already published",dest)
        return
    used=set()
    for p in existing:
        if p.get("date","")>=target.isoformat():continue
        used.update(q["id"] for q in p.get("questions",[]))
    subjects,note=day_subjects(bank,target)
    picks=[]
    counts={}
    for s in subjects:
        chosen,fresh,total=choose(bank,s,target,used,existing)
        counts[s]={"selected":len(chosen),"freshBeforeSelection":fresh,"totalEligible":total}
        if len(chosen)<10:raise RuntimeError(f"Subject {s} only {len(chosen)} verified sources; 40-question test not created")
        picks+=chosen
    assert len(picks)==40 and len({q["id"] for q in picks})==40
    repeats=sum(q["id"] in used for q in picks)
    output={
      "date":target.isoformat(),"id":"gate-daily-pyq-"+target.isoformat(),
      "title":"GATE EE/EC Actual PYQs · "+target.isoformat(),
      "questionCount":40,"durationMinutes":180,
      "subjects":subjects,"sourceYears":[2022,2023,2024,2025,2026],
      "status":"official_gate_pyqs_plus_labeled_ace_classroom_problems",
      "classificationNote":"Official GATE screenshots and keys are retained. Only subject-tagged questions approved by source-text audit or specific contextual matching enter daily technical paper selection; remaining classifications are withheld pending review. ACE classroom questions are labeled separately.",
      "rotationNote":note,
      "selectionNote":f'Selected {sum(q.get("sourceType")=="ace_classroom" for q in picks)} labeled ACE classroom questions alongside original GATE PYQs; {repeats} source question IDs were previously published.',
      "repeatCount":repeats,"selectionCounts":counts,
      "questions":picks
    }
    dest.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n")
    manifest={"schemaVersion":1,"startDate":START.isoformat(),"papers":[{"date":p["date"],"id":p["id"],"file":p["date"]+".json","repeatCount":p.get("repeatCount",0)} for p in sorted(existing+[output],key=lambda p:p["date"],reverse=True)]}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("PUBLISHED",target,len(picks),"subjects",subjects,"repeats",repeats,"note",note,flush=True)
    print("ELIGIBLE",counts,flush=True)
if __name__=="__main__":main()
