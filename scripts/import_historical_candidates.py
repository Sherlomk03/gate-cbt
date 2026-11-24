#!/usr/bin/env python3
"""Import 2020 official EE/EC as per-question review candidates (fail closed).

Only official GATE PDF and keys are used. Automatic crops and source-text tags
are not considered human-verified; nothing generated here is CBT-eligible.
This also attempts 2021 key extraction, without fake question numbering.
"""
from __future__ import annotations
import io, json, pathlib, re, hashlib, time
import fitz, requests, pdfplumber
from PIL import Image

CAT=pathlib.Path("pyq/historical/source-catalog-2010-2026.json")
STAGE=pathlib.Path("pyq/historical/staging")
CAND=pathlib.Path("pyq/historical/candidates")
CROP=pathlib.Path("pyq/historical/crops")
AGENT={"User-Agent":"Mozilla/5.0 GATE historical source importer"}
QUESTION=re.compile(r'^\s*Q\s*\.?\s*(?:No\.?\s*)?(\d{1,2})(?:\s|[.:]|$)',re.I)
SESSION={2020:4,2021:4}

def getpdf(url):
    for attempt in range(3):
        try:
            r=requests.get(url,headers=AGENT,timeout=(20,80))
            r.raise_for_status()
            if not r.content.startswith(b"%PDF"):raise ValueError("Non-PDF content")
            return r.content
        except Exception:
            if attempt==2:raise
            time.sleep(3+attempt)

def anchors(doc):
    result=[]
    for pi,pg in enumerate(doc):
        for block in pg.get_text("dict")["blocks"]:
            for line in block.get("lines",[]):
                spans=line.get("spans",[])
                if not spans:continue
                t="".join(x.get("text","") for x in spans)
                m=QUESTION.match(t)
                if not m:continue
                n=int(m.group(1))
                if not 1<=n<=55:continue
                x,y,_,_=line["bbox"]
                if y<25 or y>pg.rect.height-35:continue
                result.append((pi,round(y,2),n,t[:90]))
    return sorted(set(result))

def technical_anchors(doc,year,branch):
    allpoints=anchors(doc)
    ones=[(pi,y) for pi,y,n,t in allpoints if n==1]
    # Reliable gate for 2020: paper has GA Q1-Q10 followed by branch
    # Q1-Q55, with an explicit "Q1-Q25 carry one mark each" heading.
    headings=[]
    for pi,pg in enumerate(doc):
        for block in pg.get_text("dict")["blocks"]:
            for line in block.get("lines",[]):
                t="".join(sp.get("text","") for sp in line.get("spans",[]))
                low=t.lower().replace(" ", "")
                if "q1-q25carryonemarkeach" in low or "q1–q25carryonemarkeach" in low:
                    headings.append((pi,line["bbox"][1]))
    if headings:
        start=max(headings)
    elif len(ones)>=2:
        start=sorted(ones)[-1]   # final Q1 (not a duplicated GA label)
    else:
        return {},allpoints,False
    print("BOUNDARY",year,branch,"first Q1 locations",ones,"headings",headings,"technical start",start,flush=True)
    final={}
    for pi,y,n,t in allpoints:
        if (pi,y)<start:continue
        final.setdefault(n,(pi,y))
    return final,allpoints,(set(final)==set(range(1,56)))

def render_crop(doc,start,end,id):
    segments=[]
    pi0,y0=start
    pi1,y1=end
    if pi1<pi0 or pi1-pi0>3:raise ValueError("Inconsistent page span")
    for pi in range(pi0,pi1+1):
        pg=doc[pi]
        top=max(18,(y0-7 if pi==pi0 else 40))
        bottom=min(pg.rect.height-28,(y1-5 if pi==pi1 else pg.rect.height-30))
        if bottom-top<8:raise ValueError("Question crop too short")
        pix=pg.get_pixmap(matrix=fitz.Matrix(1.55,1.55),
                          clip=fitz.Rect(25,top,pg.rect.width-25,bottom),
                          alpha=False,colorspace=fitz.csRGB)
        segments.append(Image.frombytes("RGB",(pix.width,pix.height),pix.samples))
    width=max(i.width for i in segments);height=sum(i.height for i in segments)+12*(len(segments)-1)
    im=Image.new("RGB",(width,height),"white")
    top=0
    for seg in segments:im.paste(seg,(0,top));top+=seg.height+12
    path=CROP/id.split("-Q")[0]/(id.split("-")[-1]+".webp")
    path.parent.mkdir(parents=True,exist_ok=True)
    im.save(path,format="WEBP",quality=76,method=4)
    return str(path),pi0+1,pi1+1

def make_excerpt(doc,start,end):
    pi0,y0=start;pi1,y1=end
    parts=[]
    for pi in range(pi0,pi1+1):
        pg=doc[pi]
        top=max(15,y0-5 if pi==pi0 else 30)
        bottom=min(pg.rect.height-20,y1 if pi==pi1 else pg.rect.height-25)
        if bottom>top:
            parts.append(pg.get_text("text",clip=fitz.Rect(0,top,pg.rect.width,bottom),sort=True))
    return " ".join(" ".join(parts).split())[:3000]

def parse_text_key(raw,branch):
    doc=fitz.open(stream=raw,filetype="pdf")
    rows={}
    for page in doc:
        text=page.get_text("text",sort=True)
        for line in text.splitlines():
            line=" ".join(line.split())
            # 2021 source key: Q.No Session MCQ/MSQ/NAT Section Key Marks Negative Marks
            m=re.match(r'^(\d{1,2})\s+(\d+)\s+(MCQ|MSQ|NAT)\s+(GA|'+branch+r')\s+(.+?)\s+([12])\s+(?:0|1/3|2/3)\s*$',line,re.I)
            if not m:continue
            n,session,typ,section,key,marks=m.groups()
            n=int(n)
            if (section=="GA" and n>10) or (section==branch and n>55):continue
            rows[(section,n)]={"number":n,"section":section,"type":typ,"session":int(session),"marks":int(marks),"officialKeyAsPrinted":key}
    doc.close()
    return list(rows.values())

def main():
    cat=json.loads(CAT.read_text())
    idx=[]
    for year in (2020,2021):
      for branch in ("EC","EE"):
        id=f"{year}-{branch}"
        original=next(x for x in cat["papers"] if x["id"]==id)
        paper=getpdf(original["paperUrl"])
        doc=fitz.open(stream=paper,filetype="pdf")
        points,allpoints,complete=technical_anchors(doc,year,branch)
        staged=json.loads((STAGE/(id+".json")).read_text())
        keys=staged["extractedKeyRows"]
        if year==2021:
            key_bytes=getpdf(original["keyUrl"])
            newkeys=parse_text_key(key_bytes,branch)
            if len(newkeys)>len(keys):keys=newkeys
            print("2021 KEY EXTRACTION",id,len(keys),flush=True)
        keymap={r["number"]:r for r in keys if r["section"]==branch}
        sessions={k.get("session") for k in keys if k.get("section")==branch and k.get("session") is not None}
        session=(next(iter(sessions)) if len(sessions)==1 else SESSION[year])
        stem_candidates=[]
        if complete and len(keymap)==55:
            print("CROP ALL",id,"55 anchors and keys",flush=True)
            # Last technical Q55 runs to next source answer table or end of paper.
            for n in range(1,56):
                start=points[n]
                if n<55:end=points[n+1]
                else:
                    last_page=start[0]
                    end=(last_page,min(doc[last_page].rect.height-30,start[1]+500))
                    # End on same page only; never incorporate answer-key pages.
                sourcekey=keymap[n]
                qid=f"{year}-{branch}-S{session}-Q{n:02d}"
                try:
                    path,pstart,pend=render_crop(doc,start,end,qid)
                    extract=make_excerpt(doc,start,end)
                except Exception as exc:
                    print("CROP FAILED",qid,str(exc),flush=True)
                    continue
                stem_candidates.append({
                  "id":qid,"number":n,"section":branch,"year":year,"branch":branch,
                  "session":session,"sessionVerified":False,
                  "type":sourcekey["type"],"marks":sourcekey["marks"],
                  "officialKey":sourcekey["officialKeyAsPrinted"],
                  "keyVerifiedForQuestion":True,
                  "imagePath":path.replace("pyq/historical/",""),
                  "imageCropReviewed":False,
                  "imageAuditStatus":"automatic_boundary_needs_visual_review",
                  "imageStartPage":pstart,"imageEndPage":pend,
                  "subject":"Unclassified","topic":"Needs source audit",
                  "selectionEligible":False,
                  "taxonomyReviewStatus":"requires_manual_subject_review",
                  "classificationStatus":"unclassified",
                  "sourceExtract":extract,
                  "sourcePdfSha256":hashlib.sha256(paper).hexdigest()
                })
        result={"year":year,"branch":branch,"paperUrl":original["paperUrl"],
                "keyUrl":original.get("keyUrl") or original["paperUrl"],
                "session":session,
                "verificationStatus":"automated_candidates_not_ready_for_daily",
                "imageBase":"./pyq/historical/",
                "paperSha256":hashlib.sha256(paper).hexdigest(),
                "totalQuestionAnchors":len(points),"complete55Anchors":complete,
                "keyCount":len(keymap),"sourcePages":len(doc),
                "questions":stem_candidates,
                "eligibilityNote":"Not CBT-ready. Key rows alone do not validate images or subject labels; each candidate requires visual crop review."}
        CAND.mkdir(parents=True,exist_ok=True)
        (CAND/(id+".json")).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
        idx.append({"id":id,"keyCount":len(keymap),"anchorCount":len(points),"complete55Anchors":complete,"questionCandidates":len(stem_candidates),"cbtReady":0})
        print("RESULT",id,"allAnchors",len(allpoints),"technical",len(points),"key",len(keymap),"candidates",len(stem_candidates),flush=True)
        doc.close()
    (CAND/"index.json").write_text(json.dumps({"status":"question_images_and_keys_need_manual_audit","papers":idx},indent=2)+"\n")
if __name__=="__main__":main()
