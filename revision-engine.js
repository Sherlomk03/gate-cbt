/* GATE 2027 local-browser revision analytics, v2.
   This is a read-only lens on website CBT attempts. No exam scores or answers
   are modified, uploaded or stored on GitHub. Any history without original
   question-level grading stays qualitative.
*/
(function(root){
'use strict';
const PREFIX='gateCBT.realDaily.v1.',CHAT_KEY='gateCBT.chatHistory.v1',LEGACY_KEY='gateCBT.v2';
const REVIEW_KEY='gateCBT.revisionCards.v2';
const FIXES={
 '2023-EC-Q52':{subject:'Electromagnetics',topic:'Transmission Lines / Standing Waves'},
 '2026-EE-Q58':{subject:'Power Systems',topic:'Economic Dispatch / Transmission Losses'},
 '2025-EC-Q41':{subject:'Communication Systems',topic:'Maximum-Likelihood Symbol Detection'},
 '2024-EC-Q57':{subject:'Communication Systems',topic:'Quantization / SQNR'}
};
const ALIASES={'Mathematics':'Engineering Mathematics','Maths':'Engineering Mathematics',
 'Networks':'Network Theory','Network':'Network Theory','Signals and Systems':'Signals & Systems',
 'Signals':'Signals & Systems','Digital':'Digital Electronics','Analog':'Analog Electronics'};
function normalized(s){return String(s||'').toLowerCase().replace(/[–—]/g,'-').replace(/&/g,'and').replace(/\s+/g,' ').trim()}
function canonical(s){return ALIASES[s]||s||''}
function istDate(date){const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(date||new Date());const m=Object.fromEntries(parts.map(x=>[x.type,x.value]));return m.year+'-'+m.month+'-'+m.day}
function validDate(s){return /^\d{4}-\d{2}-\d{2}$/.test(String(s||''))}
function dateShift(date,days){const d=new Date(String(date)+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+days);return d.toISOString().slice(0,10)}
function read(key){try{const x=JSON.parse(localStorage.getItem(key)||'null');return x&&typeof x==='object'?x:null}catch{return null}}
function uniqueLetters(s){return [...new Set(String(s??'').toUpperCase().match(/[A-D]/g)||[])].sort().join('')}
function acceptedRanges(k){return String(k).replace(/[−–]/g,'-').split(/\s+OR\s+/i).flatMap(s=>{const m=s.match(/(-?\d+(?:\.\d+)?)\s+to\s+(-?\d+(?:\.\d+)?)/i);if(m)return [[Number(m[1]),Number(m[2])]];const v=Number(s.trim());return Number.isFinite(v)?[[v-.005,v+.005]]:[]})}
function grade(q,value){
 if(/\bMTA\b/i.test(String(q.officialKey)))return 'MTA';
 if(value===undefined||value===null||value===''||(Array.isArray(value)&&!value.length))return 'skipped';
 const keys=String(q.officialKey).split(/\s+OR\s+/i);let ok=false;
 if(q.type==='MCQ')ok=keys.some(k=>String(value).trim().toUpperCase()===k.trim().toUpperCase());
 else if(q.type==='MSQ')ok=keys.some(k=>uniqueLetters(Array.isArray(value)?value.join(''):value)===uniqueLetters(k));
 else if(q.type==='NAT'){const v=Number(value);ok=Number.isFinite(v)&&acceptedRanges(q.officialKey).some(([lo,hi])=>lo<=v&&v<=hi)}
 return ok?'correct':'wrong';
}
function matchPack(packs,subject,topic){
 const sub=canonical(subject),t=normalized(topic);
 if(!t||t==='unclassified'||t==='needs review')return null;
 let best=null,bestScore=0;
 for(const p of packs){
  if(p.subject!==sub)continue;
  for(const phrase of p.patterns||[]){
   const f=normalized(phrase);
   if(!f||!t.includes(f))continue;
   const generic=/^(linear algebra|probability|complex|transforms|lti|analog|digital|network|machine|amplifier|diode|signal|control|field|converter|logic)$/.test(f);
   const score=(generic?1:5)+Math.min(5,f.length/9);
   if(score>bestScore){bestScore=score;best=p}
  }
 }
 return best;
}
function hintPack(packs,text){
 const t=normalized(text);
 let sub=/fourier|parseval|sinc|z.transform|roc|sampling|convolution|lti|laplace/.test(t)?'Signals & Systems':
 /routh|root locus|stability margin|pi controller/.test(t)?'Control Systems':
 /probability|complex|matrix|linear algebra|calculus|differential equation/.test(t)?'Engineering Mathematics':
 /thevenin|rlc|network|kcl|kvl|rc transient/.test(t)?'Network Theory':
 /op.amp|mosfet|bjt/.test(t)?'Analog Electronics':
 /sequential|flip.flop|boolean|logic gate/.test(t)?'Digital Electronics':'';
 if(!sub)return null;
 return matchPack(packs,sub,t);
}
async function requestJson(url){
 const response=await fetch(url+(url.includes('?')?'&':'?')+'_='+Date.now(),{cache:'no-store'});
 if(!response.ok)throw Error('HTTP '+response.status+' fetching '+url);
 return response.json();
}
async function load(packs){
 const state={packs,rows:[],hints:[],unmapped:[],issues:[],testDates:[],published:[],today:istDate(),exam:null};
 let manifest;
 try{manifest=await requestJson('./papers/daily-pyq/manifest.json');state.published=manifest.papers||[]}
 catch(e){state.issues.push('Published paper manifest unavailable; showing cards and previously saved review checks.');return state}
 const byDate=new Map();
 for(const e of state.published)if(validDate(e.date)&&e.file)byDate.set(e.date,e);
 const eligible=[...byDate.values()].filter(e=>{const a=read(PREFIX+e.date);return !!(a?.submittedAt&&a.answers&&typeof a.answers==='object')});
 const loaded=await Promise.all(eligible.map(async e=>{
  const attempt=read(PREFIX+e.date);
  try{
   const paper=await requestJson('./papers/daily-pyq/'+encodeURIComponent(e.file));
   if(paper.date!==e.date||!Array.isArray(paper.questions)||paper.questions.length!==40)throw Error('Paper mismatch');
   return {date:e.date,paper,attempt};
  }catch(err){state.issues.push('Cannot assess saved '+e.date+': original question file unavailable.');return null}
 }));
 for(const item of loaded.filter(Boolean)){
  const {date,paper,attempt}=item;
  const drift=!!(attempt.paperRevisionId&&paper.revisionId&&attempt.paperRevisionId!==paper.revisionId);
  if(drift)state.issues.push('Saved '+date+' attempt uses an earlier revision. Only still-matching answered question IDs were assessed; other questions were not marked skipped.');
  let counted=0;
  for(const q of paper.questions){
   if(drift&&!Object.prototype.hasOwnProperty.call(attempt.answers,q.id))continue;
   const status=grade(q,attempt.answers[q.id]);if(status==='MTA')continue;
   const corrected=FIXES[q.id]||q;
   const subject=canonical(corrected.subject),topic=corrected.topic||'Unclassified';
   const row={date,id:q.id,status,subject,topic,marks:Number(q.marks)||1,sourceId:q.sourceId||q.id,sourceType:q.sourceType||'official_gate',
    imagePath:q.imagePath||null,index:paper.questions.findIndex(x=>x.id===q.id),classificationStatus:q.classificationStatus||'provisional',
    questionLink:'./daily-pyq.html?date='+encodeURIComponent(date)+'&q='+encodeURIComponent(q.id)};
   const pack=matchPack(packs,subject,topic);
   if(pack){row.packId=pack.id;state.rows.push(row)}
   else{row.packId=null;state.unmapped.push(row)}
   counted++;
  }
  if(counted)state.testDates.push(date);
 }
 // Optional imported historical study notes are qualitative, NOT scored data.
 const history=read(CHAT_KEY),recorded=new Set(state.testDates);
 if(history?.schema==='gate-chat-history-v1'&&Array.isArray(history.records)){
  for(const rec of history.records){
   if(rec.category==='daily'&&recorded.has(rec.date))continue;
   for(const label of rec.reviewTopics||[]){
    const p=hintPack(packs,label);
    if(p)state.hints.push({id:p.id,label:String(label),source:'Imported historical study notes'});
   }
  }
 }
 const legacy=read(LEGACY_KEY);
 for(const note of Array.isArray(legacy?.prior)?legacy.prior:[]){
  if(!['wrong','skipped'].includes(note?.status))continue;
  if(String(note.paperId||'').startsWith('gate-daily-pyq-')||recorded.has(note.date))continue;
  const p=matchPack(packs,canonical(note.subject),note.topic);
  if(p)state.hints.push({id:p.id,label:String(note.topic||p.title),source:'Earlier practice mistake'});
 }
 try{
  const entry=byDate.get(state.today);
  if(entry)state.exam=await requestJson('./papers/daily-pyq/'+encodeURIComponent(entry.file));
 }catch(e){state.issues.push('Today’s published subject rotation could not be loaded.')}
 return state;
}
function reviewData(){
 const saved=read(REVIEW_KEY);
 return saved&&saved.schema===2&&saved.cards&&typeof saved.cards==='object'?saved:{schema:2,cards:{}};
}
function cardReview(id,day){const state=reviewData(),row=state.cards[id]||{};
 // Old quick-revision checkboxes also count as a review, not test mastery.
 const legacy=read('gateCBT.quickRevision.v1.'+day);
 const older=Array.isArray(legacy?.ids)&&legacy.ids.includes(id);
 return {...row,reviewedToday:row.lastReviewedDate===day||older};
}
function markCard(id,action,day){
 const date=day||istDate(),log=reviewData(),old=log.cards[id]||{},dates=Array.isArray(old.reviewDates)?old.reviewDates.filter(validDate):[];
 if(action==='reviewed'){
  if(!dates.includes(date))dates.push(date);
  const lapses=Math.max(0,Number(old.lapses)||0);
  const streak=(old.lastReviewedDate&&old.lastReviewedDate!==date)?Math.max(1,Number(old.reviewStreak)||0)+1:Math.max(1,Number(old.reviewStreak)||0);
  const delay=Math.min(7,streak<=1?1:streak===2?3:7);
  log.cards[id]={...old,reviewDates:dates.slice(-25),lastReviewedDate:date,reviewStreak:streak,confidence:'reviewed',needPractice:false,nextReviewDate:dateShift(date,delay),lapses};
 }else if(action==='practice'){
  log.cards[id]={...old,confidence:'unclear',needPractice:true,nextReviewDate:date,lapses:Math.max(0,Number(old.lapses)||0)+1};
 }else if(action==='reset'){
  delete log.cards[id];
 }else throw Error('Invalid revision action');
 try{localStorage.setItem(REVIEW_KEY,JSON.stringify({...log,updatedAt:new Date().toISOString()}))}catch(e){console.warn('Revision progress cannot be saved',e)}
 // Share today's checkbox with existing 5-min revision view.
 try{
  const key='gateCBT.quickRevision.v1.'+date,from=read(key)||{},ids=new Set(Array.isArray(from.ids)?from.ids:[]);
  if(action==='reviewed')ids.add(id);
  if(action==='practice'||action==='reset')ids.delete(id);
  localStorage.setItem(key,JSON.stringify({ids:[...ids],updatedAt:new Date().toISOString()}));
 }catch(e){console.warn(e)}
}
function evaluate(state){
 const map=new Map(state.packs.map(p=>[p.id,{pack:p,correct:0,wrong:0,skipped:0,missedMarks:0,total:0,rows:[],qualitative:0,latestDate:'',lastMissDate:'',laterCorrectIds:new Set(),laterCorrectDates:new Set()}]));
 for(const r of state.rows){const a=map.get(r.packId);if(!a)continue;a.rows.push(r);a[r.status]++;a.total++;if(r.status==='wrong'||r.status==='skipped')a.missedMarks+=r.marks;if(r.date>a.latestDate)a.latestDate=r.date;if(r.status!=='correct'&&r.date>a.lastMissDate)a.lastMissDate=r.date}
 for(const a of map.values())for(const r of a.rows){
  if(r.status==='correct'&&a.lastMissDate&&r.date>a.lastMissDate){a.laterCorrectIds.add(r.id);a.laterCorrectDates.add(r.date)}
 }
 for(const h of state.hints){const v=map.get(h.id);if(v)v.qualitative++}
 return [...map.values()].map(a=>{
  const r=cardReview(a.pack.id,state.today);
  const after=a.laterCorrectIds.size;
  let status='No scored evidence';
  if(a.wrong+a.skipped){
   if(after>=2&&a.laterCorrectDates.size>=2)status='Recovery demonstrated across later tests';
   else if(after>=1)status='Improving · later correct answer';
   else status='Needs practice · missed in tests';
  }else if(a.total>=3)status='No misses in submitted tests';
  else if(a.total)status='Limited scored evidence';
  else if(a.qualitative)status='Earlier review flag · unscored';
  if(r.needPractice)status='Self-flagged · still unclear';
  const recent=a.rows.slice().sort((x,y)=>y.date.localeCompare(x.date)).slice(0,5);
  const recentMiss=recent.filter(x=>x.status==='wrong'||x.status==='skipped').length;
  const unresolved=(a.wrong+a.skipped)>0&&after<2;
  const base=unresolved?50:after>0?12:0;
  const urgency=base+a.missedMarks*2.5+recentMiss*5+Math.min(20,a.wrong*4+a.skipped*2)+Math.min(7,a.qualitative)*2
     +(r.needPractice?30:0)+(r.nextReviewDate&&r.nextReviewDate<=state.today?4:0)-Math.min(12,after*5);
  return {...a,review:r,afterCorrect:after,afterDates:a.laterCorrectDates.size,
   status,priority:Math.max(0,urgency),due:!!(r.nextReviewDate&&r.nextReviewDate<=state.today),
   currentWeak:unresolved||!!r.needPractice,improving:after>=1,verifiedRecovery:after>=2&&a.laterCorrectDates.size>=2};
 });
}
root.GateRevision={PREFIX,CHAT_KEY,LEGACY_KEY,REVIEW_KEY,read,istDate,dateShift,matchPack,grade,load,evaluate,reviewData,cardReview,markCard,canonical};
})(window);
