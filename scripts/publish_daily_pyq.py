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
            if not q.get("imagePath") or not q.get("officialKey"):continue
            if q["type"] not in ("MCQ","MSQ","NAT"):continue
            questions.append({
              "id":q["id"],"sourceId":f'GATE {source["year"]} {source["branch"]} Q{q["number"]}',
              "year":source["year"],"branch":source["branch"],"questionNumber":q["number"],
              "subject":q.get("subject") or "Unclassified","topic":q.get("topic","Needs review"),
              "classificationStatus":q.get("classificationStatus","unclassified"),
              "type":q["type"],"marks":q["marks"],"officialKey":q["officialKey"],
              "imagePath":"./pyq/five-years/"+q["imagePath"],
              "paperUrl":source["paperUrl"],"keyUrl":source["keyUrl"],
              "pdfPage":q.get("imageStartPage") or q.get("pdfPage"),
              "imageAuditStatus":q.get("imageAuditStatus","automated_crop")
            })
    return questions

def deterministic_sort(questions,day,seed):
    return sorted(questions,key=lambda q:hashlib.sha256(f'{seed}-{day.isoformat()}-{q["id"]}'.encode()).hexdigest())

def choose(items, subject, today,used,history):
    candidates=[q for q in items if q["subject"]==subject]
    distinct=[q for q in candidates if q["id"] not in used]
    selected=[]
    # Favor previously unused, sample years/branches as widely as possible.
    for pool in (distinct,[q for q in candidates if q["id"] in used]):
        for q in deterministic_sort(pool,today,subject):
            if len(selected)==10:break
            if q["id"] in {x["id"] for x in selected}:continue
            selected.append(q)
        if len(selected)==10:break
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
    bank=get_questions()
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
      "status":"official_original_screenshots_with_provisional_topic_classifications",
      "classificationNote":"Subject/topic tags are automated and provisional; official image and final key are original. No AI-generated questions.",
      "rotationNote":note,
      "selectionNote":f'Fresh PYQs are prioritized, but {repeats} previously published question IDs had to repeat because the classified pool is limited.',
      "repeatCount":repeats,"selectionCounts":counts,
      "questions":picks
    }
    dest.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n")
    manifest={"schemaVersion":1,"startDate":START.isoformat(),"papers":[{"date":p["date"],"id":p["id"],"file":p["date"]+".json","repeatCount":p.get("repeatCount",0)} for p in sorted(existing+[output],key=lambda p:p["date"],reverse=True)]}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("PUBLISHED",target,len(picks),"subjects",subjects,"repeats",repeats,"note",note,flush=True)
    print("ELIGIBLE",counts,flush=True)
if __name__=="__main__":main()
