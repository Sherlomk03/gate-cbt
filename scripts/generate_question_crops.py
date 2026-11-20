#!/usr/bin/env python3
"""Generate reviewable per-question image crops from official GATE PDFs.

These are automated crops, NOT human-verified transcriptions. Each record
retains the official PDF link, page number, and crop audit status.
"""
import json
import pathlib
import re
import time
import io
import requests
import fitz
from PIL import Image

BASE = pathlib.Path("pyq/five-years")
OUTPUT = BASE / "crops"
OUTPUT.mkdir(parents=True, exist_ok=True)
client = requests.Session()
client.headers["User-Agent"] = "Mozilla/5.0 (GATE historical paper study viewer)"
MARK = re.compile(r"^\s*Q\s*\.?\s*(\d{1,2})(?!\d)(?:\s|[.:])")
RANGE = re.compile(r"Q\s*\.?\s*\d+\s*(?:-|–|—|to)\s*Q?\s*\.?\s*\d+", re.I)

def get_pdf(url):
    for trial in range(4):
        try:
            response=client.get(url, timeout=100)
            response.raise_for_status()
            if not response.content.startswith(b"%PDF"):
                raise ValueError("Expected official PDF")
            return fitz.open(stream=response.content, filetype="pdf")
        except Exception as exc:
            if trial==3: raise
            time.sleep(3*(trial+1))

def markers(doc):
    found={n:[] for n in range(1,66)}
    for pi,p in enumerate(doc):
        d=p.get_text("dict", flags=fitz.TEXT_PRESERVE_LIGATURES)
        for block in d["blocks"]:
            for ln in block.get("lines",[]):
                spans=ln.get("spans",[])
                if not spans: continue
                txt="".join(sp["text"] for sp in spans)
                match=MARK.match(txt)
                if not match or RANGE.search(txt): continue
                n=int(match.group(1))
                if n not in found:continue
                # Exclude headings, footer, question table headers.
                if re.search(r"carry\s+(?:one|two)|mark\s+each", txt,re.I): continue
                rect=fitz.Rect(ln["bbox"])
                if rect.y0<30 or rect.y0>p.rect.height-45: continue
                found[n].append((pi,round(rect.y0,1),round(rect.x0,1)))
    return found

def crop_question(doc,q,nextq,anchors,quality=77):
    n=q["number"]
    expected=max(0,min(len(doc)-1,int(q.get("pdfPage") or 1)-1))
    candidates=anchors.get(n,[])
    if candidates:
        # Favor exact official page; estimated page pointers have lower trust.
        best=min(candidates,key=lambda x:(abs(x[0]-expected),abs(x[1]-100)))
        start_page,start_y,_=best
        status="automatic_boundary_needs_visual_review"
    else:
        start_page,start_y=expected,65
        status="page_fallback_needs_manual_crop"
    if nextq:
        end_candidates=[x for x in anchors.get(nextq["number"],[]) if x[0]>=start_page and (x[0]>start_page or x[1]>start_y+7)]
        if end_candidates:
            end_page,end_y,_=min(end_candidates,key=lambda x:(x[0],x[1]))
        else:
            # Question has no reliable subsequent marker. Keep full source page.
            end_page,end_y=start_page,doc[start_page].rect.height-48
            status="next_boundary_missing_review_crop"
    else:
        end_page,end_y=start_page,doc[start_page].rect.height-48
    if end_page<start_page or end_page-start_page>3:
        end_page,end_y=start_page,doc[start_page].rect.height-48
        status="implausible_boundary_review_crop"
    segments=[]
    for pi in range(start_page,end_page+1):
        page=doc[pi];height=page.rect.height;width=page.rect.width
        top=(start_y-8) if pi==start_page else 46
        bottom=(end_y-7) if pi==end_page else height-48
        if pi==start_page and pi==end_page and bottom<top+45:
            bottom=min(height-48,top+180)
            status="short_crop_needs_manual_review"
        top=max(30,top);bottom=min(height-30,bottom)
        if bottom<=top+6: continue
        # Include left question number and all options/diagrams, exclude page margins.
        rect=fitz.Rect(34,top,width-34,bottom)
        pix=page.get_pixmap(matrix=fitz.Matrix(1.50,1.50),clip=rect,alpha=False,colorspace=fitz.csRGB)
        image=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
        segments.append(image)
    if not segments:
        raise ValueError(f"No image region for Q{n}")
    w=max(s.width for s in segments)
    h=sum(s.height for s in segments)+max(0,len(segments)-1)*16
    merged=Image.new("RGB",(w,h),"white")
    y=0
    for seg in segments:
        merged.paste(seg,(0,y));y+=seg.height+16
    return merged,status,start_page+1,end_page+1

def main():
    index=json.loads((BASE/"manifest.json").read_text())
    total=0
    for entry in index["papers"]:
        path=BASE/entry["file"];paper=json.loads(path.read_text())
        name=f'{paper["year"]}-{paper["branch"]}'
        print("CROPPING",name,flush=True)
        doc=get_pdf(paper["paperUrl"])
        anchor=markers(doc)
        dest=OUTPUT/name;dest.mkdir(parents=True,exist_ok=True)
        fallback=0;estimated=0
        for i,q in enumerate(paper["questions"]):
            if q["number"]<=10: continue
            nextq=paper["questions"][i+1] if i+1<len(paper["questions"]) else None
            image,status,p0,p1=crop_question(doc,q,nextq,anchor)
            filename=f"Q{q['number']}.webp"
            image.save(dest/filename,format="WEBP",quality=quality if (quality:=77) else 77,method=4)
            q["imagePath"]=f"crops/{name}/{filename}"
            q["imageAuditStatus"]=status
            q["imageStartPage"]=p0
            q["imageEndPage"]=p1
            fallback+=("fallback" in status or "missing" in status or "implausible" in status)
            estimated+=(p0!=q.get("pdfPage"))
            total+=1
        paper["format"]="official_pdf_individual_image_crops"
        paper["questionSource"]="automatically cropped original official PDF; diagram and option boundaries require visual audit"
        path.write_text(json.dumps(paper,ensure_ascii=False,indent=2)+"\n")
        print("DONE",name,"55 crops", "fallback",fallback,"pointerOffset",estimated,flush=True)
        doc.close()
    print("COMPLETE",total,"images",flush=True)

if __name__=="__main__":
    main()
