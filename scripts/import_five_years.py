import io,json,re,time,pathlib
import requests,fitz,pdfplumber

ROOT=pathlib.Path('pyq/five-years'); ROOT.mkdir(parents=True,exist_ok=True)
BASE='https://gate2026.iitg.ac.in/doc/download/'
FILES={
2026:{'EE':('2026/QPs/EE.pdf','2026/Keys/EE_Keys.pdf'),'EC':('2026/QPs/EC.pdf','2026/Keys/EC_Keys.pdf')},
2025:{'EE':('2025/EE2025.pdf','2025_Key/EE_Keys.pdf'),'EC':('2025/EC2025.pdf','2025_Key/EC_Keys.pdf')},
2024:{'EE':('2024/EE24S8.pdf','2024/EEFinalAnswerKey.pdf'),'EC':('2024/EC24S7.pdf','2024/ECFinalAnswerKey.pdf')},
2023:{'EE':('2023/ee_2023.pdf','Answer_keys2023/EE_ANS_GATE2023.pdf'),'EC':('2023/ec_2023.pdf','Answer_keys2023/EC_ANS_GATE2023.pdf')},
2022:{'EE':('2022/ee_2022.pdf','Answer_keys2022/ee_2022.pdf'),'EC':('2022/ec_2022.pdf','Answer_keys2022/ec_2022.pdf')}}
S=requests.Session();S.headers['User-Agent']='Mozilla/5.0'
def fetch(url):
 for i in range(4):
  try:
   r=S.get(url,timeout=65);r.raise_for_status()
   if not r.content.startswith(b'%PDF'):raise ValueError('Not PDF')
   return r.content
  except Exception:
   if i==3:raise
   time.sleep(2*(i+1))
def clean(v):return re.sub(r'\s+',' ',str(v or '').replace('\n',' ')).strip()
def parse_key(raw):
 result={}
 with pdfplumber.open(io.BytesIO(raw)) as doc:
  for page in doc.pages:
   for table in page.extract_tables(table_settings={'vertical_strategy':'lines','horizontal_strategy':'lines'}) or []:
    for row in table:
     cells=[clean(c) for c in row];cells=[c for c in cells if c]
     if len(cells)<5 or not re.fullmatch(r'\d{1,2}',cells[0]):continue
     n=int(cells[0])
     if n<1 or n>65:continue
     k=next((i for i,c in enumerate(cells) if c in ('MCQ','MSQ','NAT')),None)
     if k is None or k+3>=len(cells):continue
     kind,section,key,mark=cells[k:k+4]
     if section not in ('GA','EE','EC') or mark not in ('1','2'):continue
     result[n]={'number':n,'type':kind,'section':section,'marks':int(mark),'officialKey':key,'keyVerifiedFromTable':True}
 return result
def question_pages(raw):
 doc=fitz.open(stream=raw,filetype='pdf');r={}
 for i,p in enumerate(doc):
  for line in p.get_text('text',sort=True).splitlines():
   m=re.match(r'^\s*Q\.?\s*(\d{1,2})(?:\s|[.:])',line)
   if m:
    n=int(m.group(1))
    if 1<=n<=65 and n not in r:r[n]=i+1
 return r,len(doc)
def main():
 manifest=[]
 for year,branches in sorted(FILES.items(),reverse=True):
  for branch,(paper,key) in branches.items():
   print('Downloading',year,branch,flush=True)
   pb,kb=fetch(BASE+paper),fetch(BASE+key)
   entries=parse_key(kb);pages,pgcount=question_pages(pb)
   if len(entries)!=65 or set(entries)!=set(range(1,66)):
    raise RuntimeError(f'{year} {branch}: official key only {len(entries)}/65; missing {sorted(set(range(1,66))-set(entries))}')
   result={'year':year,'branch':branch,'paperUrl':BASE+paper,'keyUrl':BASE+key,'paperPages':pgcount,'format':'official_pdf_linked_answer_sheet','questionSource':'official PDF shown in viewer, not transcribed','questions':[]}
   for n in range(1,66):
    q=entries[n];q.update({'id':f'{year}-{branch}-Q{n}','pdfPage':pages.get(n),'answerStatus':'official_key'})
    result['questions'].append(q)
   filename=f'{year}-{branch}.json';(ROOT/filename).write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
   manifest.append({'year':year,'branch':branch,'file':filename,'questionCount':65,'technicalCount':55,'mappedPages':len(pages)})
   print('Checked',year,branch,'65 keys and',len(pages),'page refs',flush=True)
 (ROOT/'manifest.json').write_text(json.dumps({'version':1,'status':'official_pdf_linked_answer_sheet_not_transcribed','years':[2022,2023,2024,2025,2026],'papers':manifest},indent=2)+'\n')
 print('COMPLETE',len(manifest),'papers',flush=True)
if __name__=='__main__':main()
