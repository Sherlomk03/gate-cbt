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
# Keep this syllabus focus until it is explicitly changed. Topic tags remain
# provisional: this is a source-text review, not full human verification of crops.
MATHS_FOCUS=("Linear Algebra","Probability and Statistics","Complex Variables")
# Additional source-text inspected official PYQs. Other unapproved bank entries
# remain withheld; visual-review-required entries are not silently approved.
MATHS_SOURCE_TEXT_APPROVED={
    "2022-EC-Q32","2022-EC-Q37","2022-EC-Q48",
    "2022-EE-Q40","2022-EE-Q54",
    "2023-EC-Q15","2023-EC-Q36",
    "2023-EE-Q25","2023-EE-Q45",
    "2024-EC-Q30","2024-EC-Q33","2024-EC-Q55",
    "2024-EE-Q29","2024-EE-Q30","2024-EE-Q32",
    "2025-EC-Q11","2025-EC-Q13","2025-EC-Q52","2025-EC-Q58",
    "2025-EE-Q12","2025-EE-Q36","2025-EE-Q55",
    "2026-EC-Q38","2026-EE-Q30",
}

def maths_focus_topic(q):
    if q.get("subject")!="Engineering Mathematics":return None
    topic=(q.get("topic") or "").lower()
    if "linear algebra" in topic:return "Linear Algebra"
    if "probability" in topic:return "Probability and Statistics"
    if "complex" in topic:return "Complex Variables"
    return None

def get_questions():
    questions=[]
    for path in sorted(ROOT.glob("20??-??.json")):
        source=json.loads(path.read_text())
        for q in source["questions"]:
            if q["number"]<=10:continue
            if q.get("subject") in EXCLUDED:continue
            # Focus mathematics strictly on the user's three topics. Source
            # text-screened exceptions are explicit rather than auto-approved.
            if q["subject"]=="Engineering Mathematics":
                if not maths_focus_topic(q):continue
                if q.get("selectionEligible") is not True and q["id"] not in MATHS_SOURCE_TEXT_APPROVED:continue
            elif q.get("selectionEligible") is not True:continue
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
              "mathsFocusTopic":maths_focus_topic(q),
              "mathsFocusSourceTextScreened":q["id"] in MATHS_SOURCE_TEXT_APPROVED,
              "sourceExcerpt":(q.get("sourceExtract") or "")[:220],
              "type":q["type"],"marks":q["marks"],"officialKey":q["officialKey"],
              "imagePath":"./pyq/five-years/"+q["imagePath"],
              "paperUrl":source["paperUrl"],"keyUrl":source["keyUrl"],
              "pdfPage":q.get("imageStartPage") or q.get("pdfPage"),
              "imageAuditStatus":q.get("imageAuditStatus","automated_crop")
            })
    return questions


def get_ace_signals():
    """Use only the existing user-supplied ACE Signals classroom questions.

    They are NOT official GATE PYQs. Keys were solved independently;
    do not imply they are official GATE answer keys.
    """
    path=pathlib.Path("practice/ace-signals-2022.json")
    source=json.loads(path.read_text())
    allowed={1,2,3,4,5,6,8,9,10,11,12,13,14,15,16,17,18}
    output=[]
    for q in source["questions"]:
        if q["number"] not in allowed or q.get("answer") is None:
            continue
        if q.get("type") not in ("MCQ","MSQ","NAT"):continue
        output.append({
          "id":q["id"],"sourceId":f'ACE 2022 Signals & Systems Q{q["number"]}',
          "year":2022,"branch":"ACE EEE","questionNumber":q["number"],
          "subject":"Signals & Systems","topic":q["topic"],
          "classificationStatus":"user_supplied_classroom_test",
          "sourceType":"ace_classroom","officialGatePYQ":False,
          "answerStatus":q.get("answerStatus","independently_solved_not_official_key"),
          "type":q["type"],"marks":q["marks"],
          "officialKey":",".join(q["answer"]) if isinstance(q["answer"],list) else str(q["answer"]),
          "stem":q["stem"],"options":q.get("options",[]),
          "imagePath":None,"paperUrl":None,"keyUrl":None,
          "pdfPage":q["sourcePages"],
          "sourceNote":"ACE Engineering Academy 2022 classroom test supplied by user; independently solved key, not an official GATE answer key."
        })
    return output


def deterministic_sort(questions,day,seed):
    return sorted(questions,key=lambda q:hashlib.sha256(f'{seed}-{day.isoformat()}-{q["id"]}'.encode()).hexdigest())

def choose(items, subject, today, used, history):
    candidates=[q for q in items if q["subject"]==subject]
    fresh=[q for q in candidates if q["id"] not in used]
    selected=[]
    if subject=="Engineering Mathematics":
        # Spread maths across all three requested areas, without repeating a
        # previously published question while any unused focus PYQ is available.
        quotas=[("Linear Algebra",4),("Probability and Statistics",3),("Complex Variables",3)]
        for focus,quota in quotas:
            pool=[q for q in fresh if q.get("mathsFocusTopic")==focus]
            # Prefer EC sources for shared GATE EE/EC subjects.
            ordered=sorted(pool,key=lambda q:(q["branch"]!="EC",hashlib.sha256(f'maths-{focus}-{today}-{q["id"]}'.encode()).hexdigest()))
            selected+=ordered[:quota]
        picked={q["id"] for q in selected}
        for q in deterministic_sort([q for q in fresh if q["id"] not in picked],today,"maths-unused"):
            if len(selected)>=10:break
            selected.append(q)
        picked={q["id"] for q in selected}
        for q in deterministic_sort([q for q in candidates if q["id"] in used and q["id"] not in picked],today,"maths-repeat"):
            if len(selected)>=10:break
            selected.append(q)
    elif subject=="Signals & Systems":
        # Up to four clearly labeled ACE classroom questions and six official
        # GATE PYQs. A missing classroom item is never fabricated or mislabelled.
        for source_type,limit in (("ace_classroom",4),("official",6)):
            pool=[q for q in candidates if (q.get("sourceType")=="ace_classroom")==(source_type=="ace_classroom")]
            seen=set(q["id"] for q in selected)
            ordered=(deterministic_sort([q for q in pool if q["id"] not in used and q["id"] not in seen],today,subject+source_type+"fresh")+
                     deterministic_sort([q for q in pool if q["id"] in used and q["id"] not in seen],today,subject+source_type+"repeat"))
            selected.extend(ordered[:limit])
        # Refill any unfilled classroom allotment with real GATE PYQs.
        seen=set(q["id"] for q in selected)
        for q in deterministic_sort([q for q in candidates if q["id"] not in used and q["id"] not in seen],today,subject+"fill"):
            if len(selected)>=10:break
            selected.append(q)
        seen=set(q["id"] for q in selected)
        for q in deterministic_sort([q for q in candidates if q["id"] in used and q["id"] not in seen],today,subject+"fillrepeat"):
            if len(selected)>=10:break
            selected.append(q)
    else:
        for q in deterministic_sort(fresh,today,subject+"fresh"):
            if len(selected)>=10:break
            selected.append(q)
        picked={q["id"] for q in selected}
        for q in deterministic_sort([q for q in candidates if q["id"] in used and q["id"] not in picked],today,subject+"repeat"):
            if len(selected)>=10:break
            selected.append(q)
    return selected,len(fresh),len(candidates)

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
      "classificationNote":"Only original 2022–2026 GATE EE/EC PYQs with source screenshots and matched official keys, plus clearly labeled user-supplied ACE Signals classroom problems with independently solved keys (not official GATE PYQs). No AI-generated questions. Subject/topic tags remain provisional and some crops require visual review.",
      "rotationNote":note,
      "selectionNote":f'{40-sum(q.get("sourceType")=="ace_classroom" for q in picks)} official GATE PYQs and {sum(q.get("sourceType")=="ace_classroom" for q in picks)} clearly labeled ACE classroom questions. Mathematics: Linear Algebra, Probability and Statistics, Complex Variables only. {repeats} source question IDs were previously published.',
      "repeatCount":repeats,"selectionCounts":counts,
      "questions":picks
    }
    dest.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n")
    manifest={"schemaVersion":1,"startDate":START.isoformat(),"papers":[{"date":p["date"],"id":p["id"],"file":p["date"]+".json","repeatCount":p.get("repeatCount",0)} for p in sorted(existing+[output],key=lambda p:p["date"],reverse=True)]}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("PUBLISHED",target,len(picks),"subjects",subjects,"repeats",repeats,"note",note,flush=True)
    print("ELIGIBLE",counts,flush=True)
if __name__=="__main__":main()
