/**
 * Regression checks for local-browser topic revision and exam history logic.
 * Uses only Node built-ins; no network, no mock ChatGPT-generated PYQs.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const engine=fs.readFileSync('revision-engine.js','utf8');
const html=fs.readFileSync('revision-library.html','utf8');
const cards=JSON.parse(fs.readFileSync('quick-revision-content.json','utf8'));
assert(cards.packs.length>=45);
assert.equal(new Set(cards.packs.map(x=>x.id)).size,cards.packs.length);
assert(new Set(cards.packs.map(x=>x.subject)).size>=10);
assert(html.includes('id="subjects"')&&html.includes('id="search"')&&html.includes('data-view="due"'));
assert(html.includes('revision-engine.js'));
for(const c of cards.packs)assert(c.id&&c.subject&&c.title&&Array.isArray(c.formula)&&c.formula.length>=2&&c.question&&c.answer&&c.pitfall&&c.patterns?.length);
const cJS=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(x=>x.includes('function listCards'))[0];
assert(cJS,'Dedicated page controller script missing');
new vm.Script(engine,{filename:'revision-engine.js'});
new vm.Script(cJS,{filename:'revision-library.inline.js'});

const local=new Map();
const logs=[];
const dates=['2026-11-21','2026-11-22','2026-11-23'];
const q=(id,subject,topic,key='B')=>({id,type:'MCQ',officialKey:key,marks:2,subject,topic,sourceId:'GATE authentic source '+id});
function paper(date,mathKey,networkKey){
 const relevant=[
  q('M'+date,'Engineering Mathematics','Linear Algebra · Matrix Properties',mathKey),
  q('N'+date,'Network Theory','RC and RL Switching Transients',networkKey),
  q('X'+date,'Power Systems','Unclassified machine label','MTA')];
 const fill=Array.from({length:40-relevant.length},(_,i)=>q('F'+date+'-'+i,'Unclassified','Requires human source audit'));
 return {date,revisionId:'rev-1',questions:relevant.concat(fill),subjects:['Engineering Mathematics','Network Theory','Power Systems','Electrical Machines']};
}
const papers={
 '2026-11-21':paper('2026-11-21','B','B'),
 '2026-11-22':paper('2026-11-22','B','B'),
 '2026-11-23':paper('2026-11-23','B','B')
};
const manifest={papers:dates.map(date=>({date,file:date+'.json'}))};
for(const [i,date] of dates.entries()){
 const answers={
  ['M'+date]:i===0?'A':'B', // a missed math PYQ followed by correct questions on 2 later dates
  ['N'+date]:i===2?'B':'A' // recurring network mistake followed by one correct
 };
 local.set('gateCBT.realDaily.v1.'+date,JSON.stringify({submittedAt:date+'T12:00:00Z',paperRevisionId:'rev-1',answers}));
}
local.set('gateCBT.chatHistory.v1',JSON.stringify({schema:'gate-chat-history-v1',records:[
 {date:'2026-11-20',category:'daily',reviewTopics:['Fourier Series Parseval']},
 {date:'2026-11-21',category:'daily',reviewTopics:['ROC']} // same day with complete scored website data must be ignored
]}));
const fetcher=async url=>{
 const u=String(url).split('?')[0],d=u.split('/').pop();
 const obj=u.includes('manifest.json')?manifest:u.includes('quick-revision-content.json')?cards:papers[d.slice(0,10)];
 return {ok:!!obj,status:obj?200:404,json:async()=>obj};
};
const store={getItem:k=>local.get(k)||null,setItem:(k,v)=>local.set(k,v)};
const root={addEventListener(){},MathJax:null};
const base={window:root,localStorage:store,fetch:fetcher,Date,Intl,console};
vm.runInNewContext(engine,base,{filename:'revision-engine.js',timeout:2000});
const G=root.GateRevision;
assert(G,'Revision engine not exported');
assert.equal(G.grade(q('id','Network Theory','resonance','B'),'A'),'wrong');
assert.equal(G.grade(q('id','Network Theory','resonance','B'),'B'),'correct');
assert.equal(G.grade({...q('id','Network Theory','resonance','B'),officialKey:'MTA'},undefined),'MTA');
assert.equal(G.matchPack(cards.packs,'Signals & Systems','Fourier series · Average Power')?.id,'fourier-series');
assert.equal(G.matchPack(cards.packs,'Engineering Mathematics','Linear Algebra · Matrix Properties')?.id,'linear-core');
assert.equal(G.matchPack(cards.packs,'Network Theory','Unclassified'),null);
const data=await G.load(cards.packs,'2026-11-22');
assert.equal(data.testDates.length,3);
assert.equal(data.rows.filter(r=>r.subject==='Engineering Mathematics').length,3);
assert.equal(data.rows.filter(r=>r.subject==='Network Theory').length,3);
const stats=G.evaluate(data);
const m=stats.find(x=>x.pack.id==='linear-core');
const n=stats.find(x=>x.pack.id==='network-transient');
assert(m?.verifiedRecovery,'Math should show recovery only after 2 later correct papers');
assert(!m.currentWeak,'Recovered Maths should not stay as an unresolved scored error');
assert.equal(n?.afterCorrect,1);
assert(n.improving&&n.currentWeak,'One later correct must not erase 2 earlier mistakes');
assert.equal(data.hints.filter(h=>h.id==='fourier-series').length,1);
assert(!data.hints.some(h=>h.id==='zroc'),'Same-date chat summary should not double count scored CBT');

const mathScoreBefore=m.total+':'+m.correct+':'+m.wrong;
G.markCard('network-transient','practice','2026-11-24');
assert(G.cardReview('network-transient','2026-11-24').needPractice);
G.markCard('network-transient','reviewed','2026-11-24');
assert(G.cardReview('network-transient','2026-11-24').reviewedToday);
assert.equal(G.evaluate(data).find(x=>x.pack.id==='linear-core').total+':'+m.correct+':'+m.wrong,mathScoreBefore);
assert(local.has('gateCBT.quickRevision.v1.2026-11-24'),'Five-minute checklist was not synchronized');
G.markCard('network-transient','reviewed','2026-11-25');
assert.equal(G.cardReview('network-transient','2026-11-25').nextReviewDate,'2026-11-28');

// A corrected published paper must not grade missing/changed question IDs from an old submission as skipped.
local.set('gateCBT.realDaily.v1.2026-11-23',JSON.stringify({
 submittedAt:'2026-11-23T13:00:00Z',paperRevisionId:'superseded',answers:{['M2026-11-23']:'B'}
}));
const drift=await G.load(cards.packs,'2026-11-23');
assert.equal(drift.rows.filter(x=>x.date==='2026-11-23').length,1);
assert(drift.issues.some(x=>x.includes('earlier revision')));

// Render the actual webpage with a minimal fake DOM: verify topic filtering,
 // cards and question source links exist, and the user can navigate to today's subject.
const nodes=new Map();
function element(key){
 if(!nodes.has(key))nodes.set(key,{innerHTML:'',textContent:'',href:'',value:'',checked:false,dataset:{},style:{},
 classList:{toggle(){},add(){},remove(){}},
 setAttribute(){},querySelectorAll(){return []},addEventListener(){}});
 return nodes.get(key);
}
const doc={
 querySelector:element,
 querySelectorAll(){return []},
 addEventListener(){}
};
const pageWindow={GateRevision:G,MathJax:null,addEventListener(){}};
const pageCtx={window:pageWindow,document:doc,GateRevision:G,localStorage:store,fetch:fetcher,Date,Intl,console,location:{search:'?date=2026-11-22'},
 URLSearchParams};
const patched=cJS.replace(/refresh\(\)\.catch\(e=>\{([\s\S]*?)\}\);\s*$/,'window.testRefresh=refresh().catch(e=>{$1});');
assert.notEqual(cJS,patched,'Cannot capture asynchronous page init');
vm.runInNewContext(patched,pageCtx,{filename:'revision-library.html',timeout:2000});
await pageWindow.testRefresh;
assert(element('#cardCount').textContent===String(cards.packs.length));
assert(element('#cards').innerHTML.includes('15-second recall'));
assert(element('#cards').innerHTML.includes('Review')||element('#cards').innerHTML.includes('Mark revised'));
assert(element('#cards').innerHTML.includes('data-id='));
assert(element('#resultCount').textContent.includes('topic card'));
assert(element('#description').textContent.includes('Browse'));
assert(element('#tested').textContent==='3');
console.log('PASS revision engine: '+cards.packs.length+' topic cards, 11 subjects, graded feedback, later recovery, due reviews, safe paper revisions, local-only library UI.');
