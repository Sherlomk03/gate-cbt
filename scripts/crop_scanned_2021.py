#!/usr/bin/env python3
"""Locate technical questions in image-only 2021 EE/EC official GATE papers.

Each PDF page is already preserved as its source-scan image. OCR is used ONCE
per page solely to locate question labels, not to invent text or answers.
Only visually read official-key records are used; no automated crop is enabled
for daily CBT until its entire source and key are checked.
"""
from __future__ import annotations
import json,pathlib,re,collections
from PIL import Image
import pytesseract
from pytesseract import Output

ROOT=pathlib.Path("pyq/historical")
PAGE=ROOT/"source-pages"
OUT=ROOT/"candidates"
CROPS=ROOT/"crops"
KEYS=ROOT/"keys-reviewed"
QRE=re.compile(r"^Q\.?\s*(\d{1,2})$",re.I)

def ocr_anchors(src):
    pages=sorted((PAGE/src).glob("p*.webp"))
    result=[]
    for pi,path in enumerate(pages):
        im=Image.open(path).convert("RGB")
        # Question labels appear within the left-hand column of official PDF.
        left=im.crop((0,0,int(im.width*0.34),im.height))
        data=pytesseract.image_to_data(left,config="--psm 11",output_type=Output.DICT)
        lines=collections.defaultdict(list)
        for i,word in enumerate(data["text"]):
            word=word.strip()
            if not word:continue
            idx=(data["block_num"][i],data["par_num"][i],data["line_num"][i])
            lines[idx].append((data["left"][i],data["top"][i],word))
        matches=[]
        for chunks in lines.values():
            chunks.sort()
            words=[w for _,_,w in chunks]
            possible=["".join(words)," ".join(words)]
            for i,w in enumerate(words):
                if w.lower().startswith("q"):possible.append(w)
                if i+1<len(words) and w.lower().startswith("q"):possible.append(w+" "+words[i+1])
            for candidate in possible:
                clean=candidate.replace("No.","").replace("No","")
                m=QRE.match(clean.replace(" ",""))
                if not m:continue
                n=int(m.group(1))
                if not 1<=n<=55:continue
                y=min(t for _,t,_ in chunks)
                matches.append((pi,y,n))
                break
        for x in sorted(set(matches)):
            result.append(x)
        print("PAGE",src,path.name,"labels",sorted(set((n for _,_,n in matches))),flush=True)
    return sorted(result),pages

def technical_only(allq):
    q1=[(p,y) for p,y,n in allq if n==1]
    if len(q1)<2:
        return {},False,"Did not find both GA and technical Q1"
    # The later Q1 follows the General Aptitude section in 2021 EE and EC.
    start=sorted(q1)[-1]
    selected=[(p,y,n) for p,y,n in allq if (p,y)>=start]
    found={}
    last_n=0
    for pi,y,n in selected:
        if n<=last_n:continue
        found[n]=(pi,y)
        last_n=n
    return found,set(found)==set(range(1,56)),None

def crop(pathlist,start,end,src,n):
    pieces=[]
    for pi in range(start[0],end[0]+1):
        im=Image.open(pathlist[pi]).convert("RGB")
        upper=max(15,start[1]-14 if pi==start[0] else 36)
        lower=min(im.height-22,end[1]-14 if pi==end[0] else im.height-32)
        if lower<=upper+20:continue
        pieces.append(im.crop((15,upper,im.width-15,lower)))
    if not pieces:return None
    width=max(z.width for z in pieces)
    height=sum(z.height for z in pieces)+8*(len(pieces)-1)
    target=Image.new("RGB",(width,height),"white")
    y=0
    for piece in pieces:target.paste(piece,(0,y));y+=piece.height+8
    dest=CROPS/src/f"Q{n:02d}.webp"
    dest.parent.mkdir(parents=True,exist_ok=True)
    target.save(dest,format="WEBP",quality=78,method=4)
    return str(dest.relative_to(ROOT))

def build(src,branch,session,year):
    anchors,paths=ocr_anchors(src)
    found,complete,issue=technical_only(anchors)
    keys=json.loads((KEYS/f"{src}-S{session}.json").read_text())["questions"]
    key_by_n={q["number"]:q for q in keys}
    questions=[]
    for n in range(1,56):
        if n not in found:continue
        a=found[n]
        later=next((m for m in range(n+1,56) if m in found),None)
        if later is None:
            # Never overflow into a later answer key or unrelated source page.
            pi=a[0]
            im=Image.open(paths[pi])
            b=(pi,im.height-24)
        else:
            b=found[later]
        if b[0]-a[0]>2:continue
        imagePath=crop(paths,a,b,src,n)
        if imagePath is None:continue
        key=key_by_n[n]
        questions.append({
          "id":f"{src}-S{session}-Q{n:02d}",
          "year":year,"branch":branch,"session":session,"number":n,"section":branch,
          "type":key["type"],"marks":key["marks"],"officialKey":key["officialKey"],
          "marksToAll":key["marksToAll"],"keyVerifiedForQuestion":False,
          "sessionVerified":False,"imagePath":imagePath,"imageStartPage":a[0]+1,
          "imageEndPage":b[0]+1,"imageCropReviewed":False,
          "imageAuditStatus":"ocr_located_source_photo_needs_manual_review",
          "sourceType":"official_gate","selectionEligible":False,
          "subject":"Unclassified","topic":"Requires subject audit",
          "taxonomyReviewStatus":"source_image_review_pending"
        })
    report={
      "year":year,"branch":branch,"session":session,"paperSource":"official_gat​e_paper_scans",
      "questionPhotoSource":f"pyq/historical/source-pages/{src}",
      "officialKeySource":str(KEYS/f"{src}-S{session}.json"),
      "totalDetectedLabels":len(found),"technicalQuestionLabelsComplete":complete,
      "notes":"OCR located boundaries only; original photographic question screenshots and manually transcribed official key rows. Crops/keys not linked for grading without image-level audit.",
      "verificationStatus":"automatic_scanned_question_candidates_not_ready_for_daily",
      "questions":questions
    }
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/f"{src}.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("RESULT",src,"detected",len(found),"crops",len(questions),"complete",complete,issue,flush=True)
    return report

def main():
    out=[build("2021-EC","EC",4,2021),build("2021-EE","EE",3,2021)]
    indexed=OUT/"index.json"
    if indexed.exists():summary=json.loads(indexed.read_text())
    else:summary={"papers":[]}
    rem={x["id"]:x for x in summary.get("papers",[])}
    for doc in out:
        key=f'{doc["year"]}-{doc["branch"]}'
        rem[key]={"id":key,"keyCount":55,"anchorCount":doc["totalDetectedLabels"],
                  "complete55Anchors":doc["technicalQuestionLabelsComplete"],
                  "questionCandidates":len(doc["questions"]),"cbtReady":0}
    summary["papers"]=sorted(rem.values(),key=lambda x:x["id"])
    summary["status"]="Automated 2021 scanned crops require independent visual source+key audit; none enabled"
    indexed.write_text(json.dumps(summary,indent=2)+"\n")
if __name__=="__main__":main()
