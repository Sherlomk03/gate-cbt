#!/usr/bin/env python3
"""Classify original EE/EC PYQs by source PDF content.
Tags are automatic/provisional, and not certified syllabus judgments.
No AI-generated questions are added. Keep source PDF + screenshot in every record.
"""
import json,re,pathlib,time
import fitz,requests

ROOT=pathlib.Path("pyq/five-years")
S=requests.Session();S.headers['User-Agent']='Mozilla/5.0'
# Labels and keyword patterns have deliberate specificity: ambiguity -> "Unclassified".
SUBJECT_RULES={
"Engineering Mathematics":[
(13,r'\b(eigenvalues?|eigenvectors?|determinants?|rank of|singular matrix|invertible matrix|matrix is|matrices are|characteristic polynomial)\b','Linear Algebra'),
(13,r'\b(probability|probabilities|random variable|conditional expectation|joint density|cumulative distribution|gaussian distribution|poisson distribution|bayes|variance|expectation)\b','Probability and Statistics'),
(12,r'\b(analytic function|cauchy.riemann|residue theorem|complex plane|complex contour|holomorphic|entire function|complex differentiab)\b','Complex Variables'),
(12,r'\b(partial differential equation|ordinary differential equation|differential equation|initial value problem|first.order ode|second.order ode)\b','Differential Equations'),
(12,r'\b(double integral|triple integral|directional derivative|gradient vector|divergence theorem|stokes theorem|line integral|stationary point|local maximum|minima|maxima|lagrange multiplier)\b','Calculus'),
(12,r'\b(gamma function|beta function|limit of the sequence|converges absolutely|infinite series|power series|taylor series|maclaurin series)\b','Calculus and Series'),
(10,r'\b(vector space|linear independence|basis of|null space|rank.nullity|orthogonal matrix|diagonalizable)\b','Linear Algebra')
],
"Network Theory":[
(14,r'\b(thevenin|th[eé]venin|norton|superposition|maximum power transfer|millman|star.delta|delta.star)\b','Network Theorems'),
(15,r'\b(two.port|two port|z.parameters|y.parameters|h.parameters|abcd parameters|transmission parameters|reciprocity condition|network parameter)\b','Two-Port Networks'),
(14,r'\b(kirchhoff|node voltage|nodal analysis|mesh current|mesh analysis|dependent source|controlled voltage source|controlled current source)\b','Network Analysis'),
(15,r'\b(impedance seen|equivalent impedance|input impedance|driving.point impedance|bridge network|wheatstone bridge)\b','Network Functions'),
(15,r'\b(mutual inductance|mutually coupled|coupled inductors|coefficient of coupling)\b','Magnetically Coupled Circuits'),
(12,r'\b(rc circuit|rl circuit|rlc circuit|series rlc|parallel rlc|resonant frequency|quality factor|damping ratio|transient response)\b','AC Circuits and Transients'),
(10,r'\b(bode plot|bode magnitude|transfer function of the circuit|pole.zero plot|zero.input response)\b','Network Functions and Filters'),
(9,r'\b(current through the resistor|voltage across the resistor|resistors are connected|resistive network|electric circuit)\b','Circuit Analysis')
],
"Signals & Systems":[
(14,r'\b(z.transform|dtft|dft|fourier transform|fourier series|discrete time signal|discrete.time signal|discrete-time lti|signal x\[n\]|x\[n\]|h\[n\]|convolution|impulse response|sampling theorem|nyquist sampling)\b','Transforms and LTI Systems'),
(13,r'\b(unit impulse|unit step response|laplace transform|time-invariant|time invariant system|power spectral density|autocorrelation function|sampling frequency|aliasing)\b','LTI Systems and Sampling'),
(9,r'\b(sinc function|fourier spectrum|continuous.time lti)\b','Fourier Analysis')
],
"Digital Electronics":[
(15,r'\b(boolean expression|boolean algebra|logic gate|flip.flop|multiplexer|decoder|karnaugh|k.map|truth table|logic circuit|binary counter|finite state machine)\b','Combinational and Sequential Logic'),
(13,r'\b(quantization|analog.to.digital converter|adc|digital.to.analog converter|dac)\b','Converters'),
(12,r'\b(cmos logic|logic levels|setup time|hold time|propagation delay|binary representation|two.s complement)\b','Digital Logic')
],
"Analog Electronics":[
(16,r'\b(operational amplifier|op.amp|differential amplifier|common.source|common.gate|common.drain|common.emitter|common.base|common.collector)\b','Amplifiers and Op-Amps'),
(13,r'\b(mosfet|bjt|transistor bias|transconductance|small.signal|gain bandwidth|current mirror)\b','Transistor Amplifiers'),
(13,r'\b(diode circuit|pn junction|zener diode|rectifier circuit|diode connected|clipper|clamping circuit)\b','Diode Circuits'),
(13,r'\b(semiconductor|carrier concentration|fermi level|minority carrier|electron mobility|depletion region|doping concentration)\b','Semiconductor Devices'),
(10,r'\b(oscillator circuit|active filter|feedback amplifier|barkhausen)\b','Oscillators and Feedback')
],
"Electrical Machines":[
(18,r'\b(induction motor|synchronous motor|synchronous machine|alternator|transformer|dc motor|dc generator|three.phase machine|autotransformer)\b','Electrical Machines'),
(15,r'\b(slip frequency|rotor speed|slip of the motor|torque.speed|rotor resistance)\b','Induction Machines')
],
"Power Systems":[
(17,r'\b(load flow|power flow|transmission line|bus admittance|bus impedance|symmetrical components|fault current|short.circuit fault|relay setting)\b','Power System Analysis'),
(15,r'\b(per.unit|per unit|power grid|grid frequency|power factor correction|power system stability|reactive power compensation|distribution feeder)\b','Power System Operation'),
(12,r'\b(pv bus|pq bus|slack bus|swing bus)\b','Load Flow')
],
"Power Electronics":[
(17,r'\b(chopper|buck converter|boost converter|thyristor|scr|inverter output|firing angle|controlled rectifier|pwm inverter|dc.dc converter|power electronic)\b','Converters and Drives'),
(12,r'\b(switching frequency|switching losses|mosfet switch|igbt|triac)\b','Power Semiconductor Switching')
],
"Control Systems":[
(16,r'\b(root locus|nyquist stability|routh hurwitz|bode phase margin|closed.loop control system|controllability|observability|state space model)\b','Control Systems')
],
"Communication Systems":[
(17,r'\b(modulation|demodulation|qam|psk|amplitude modulation|frequency modulation|error probability|bit error rate|matched filter|hamming code)\b','Communication Theory'),
(14,r'\b(channel capacity|information entropy|huffman coding|channel coding)\b','Information Theory')
],
"Electromagnetics":[
(15,r'\b(maxwell equations|electric flux density|magnetic flux density|waveguide|poynting|dielectric interface|electromagnetic wave|transmission line characteristic impedance)\b','Electromagnetic Fields'),
(11,r'\b(electric field intensity|magnetic field intensity|electric potential|gauss law)\b','Electrostatics and Magnetostatics')
],
"Microprocessors":[
(16,r'\b(microprocessor|instruction set|address bus|memory mapped|assembly language|interrupt service routine)\b','Microprocessors')
]
}
MARKER=re.compile(r'^\s*Q\s*\.?\s*(\d{1,2})(?!\d)(?:\s|[.:])',re.I)
def fetch(url):
 for n in range(4):
  try:
   r=S.get(url,timeout=90);r.raise_for_status()
   if not r.content.startswith(b'%PDF'):raise RuntimeError('Not a valid PDF')
   return fitz.open(stream=r.content,filetype="pdf")
  except Exception:
   if n==3:raise
   time.sleep(2+n*2)
def question_text(doc):
 pts={}
 for i,page in enumerate(doc):
  for block in page.get_text("dict")["blocks"]:
   for line in block.get("lines",[]):
    spans=line.get("spans",[])
    if not spans:continue
    line_text=''.join(x.get("text","") for x in spans)
    m=MARKER.match(line_text)
    if not m:continue
    number=int(m.group(1))
    if not 1<=number<=65:continue
    y=line["bbox"][1]
    if y>page.rect.height-35:continue
    pts.setdefault(number,[]).append((i,y))
 result={}
 for n in range(1,66):
  if n not in pts:continue
  start=sorted(pts[n])[0]
  if n+1 in pts:
   candidates=[x for x in pts[n+1] if x>=start]
   end=min(candidates) if candidates else (start[0],doc[start[0]].rect.height-35)
  else:end=(start[0],doc[start[0]].rect.height-35)
  if end[0]-start[0]>3:end=(start[0],doc[start[0]].rect.height-35)
  parts=[]
  for pi in range(start[0],end[0]+1):
   pg=doc[pi]
   y0=start[1] if pi==start[0] else 30
   y1=end[1] if pi==end[0] else pg.rect.height-30
   if y1<=y0+4:continue
   raw=pg.get_text('text',clip=fitz.Rect(0,y0,pg.rect.width,y1),sort=True)
   parts.append(raw)
  result[n]=' '.join(' '.join(parts).split())[:6500]
 return result
def classify(stem,branch):
 text=stem.lower()
 scores=[]
 for subject,rules in SUBJECT_RULES.items():
  if branch=="EC" and subject in ("Power Systems","Electrical Machines","Power Electronics"):continue
  candidates=[(w,topic) for w,rx,topic in rules if re.search(rx,text,re.I)]
  score=sum(w for w,_ in candidates)
  if score:scores.append((score,subject,max(candidates)[1]))
 if not scores:return ("Unclassified","Topic requires review","unclassified",0)
 scores.sort(reverse=True)
 best=scores[0];second=scores[1][0] if len(scores)>1 else 0
 confidence="high_auto" if best[0]>=14 and best[0]>=second+5 else "provisional"
 return best[1],best[2],confidence,best[0]-second
def main():
 stats={}
 for file in sorted(ROOT.glob('20??-??.json')):
  paper=json.loads(file.read_text())
  print('CLASSIFY',paper['year'],paper['branch'],flush=True)
  doc=fetch(paper['paperUrl']); texts=question_text(doc);doc.close()
  counts={}
  for q in paper['questions']:
   if q['number']<=10:continue
   raw=texts.get(q['number'],'')
   sub,topic,confidence,margin=classify(raw,paper['branch'])
   q.update({'subject':sub,'topic':topic,'classificationStatus':confidence,
             'classificationMethod':'keyword scoring on original official PDF; review required',
             'classificationMargin':margin,'sourceExtract':raw[:1800]})
   counts[sub]=counts.get(sub,0)+1
  file.write_text(json.dumps(paper,indent=2,ensure_ascii=False)+'\n')
  stats[file.stem]=counts
  print('COUNTS',file.stem,counts,flush=True)
 (ROOT/'taxonomy-summary.json').write_text(json.dumps({'status':'provisional_machine_classification','byPaper':stats},indent=2)+'\n')
if __name__=='__main__':main()
