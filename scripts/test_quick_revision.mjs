/**
 * Offline smoke tests for the actual pre-exam revision page.
 * Uses Node's built-in vm with a small DOM/storage shim; no browser or npm deps.
 */
import fs from "node:fs";
import assert from "node:assert/strict";
import vm from "node:vm";

const html=fs.readFileSync("quick-revision.html","utf8");
const library=JSON.parse(fs.readFileSync("quick-revision-content.json","utf8"));
const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(Boolean);
const code=scripts[scripts.length-1];
assert(code.includes("loadSiteResults"),"Missing submission results integration");
assert(code.includes("reviewTopics"),"Missing historical feedback integration");
assert(html.includes("quick-revision-content.json"));
assert(html.includes('id="examLink"'));
assert(html.includes("mathjax@3"));
assert(library.packs.length>=25,"Too few curated formula packs");
const seenIds=new Set();
for(const pack of library.packs){
 assert(pack.id&&!seenIds.has(pack.id),"Duplicate or empty pack ID: "+pack.id);
 seenIds.add(pack.id);
 assert(pack.subject&&pack.title&&pack.patterns.length>0&&pack.formula.length>=2);
 assert(pack.pitfall&&pack.question&&pack.answer);
}
const p24=JSON.parse(fs.readFileSync("papers/daily-pyq/2026-11-24.json","utf8"));
const p25=JSON.parse(fs.readFileSync("papers/daily-pyq/2026-11-25.json","utf8"));
const manifest=JSON.parse(fs.readFileSync("papers/daily-pyq/manifest.json","utf8"));
assert(manifest.papers.some(x=>x.date==="2026-11-25"));
function answered(q){
 if(q.type==="MCQ")return String(q.officialKey).split(/\s+OR\s+/)[0].trim();
 if(q.type==="MSQ")return (String(q.officialKey).match(/[A-D]/g)||[]);
 const numeric=String(q.officialKey).match(/-?\d+(?:\.\d+)?/);
 return numeric?numeric[0]:"0";
}
function testEnvironment(attempt){
 const nodes=new Map();
 function el(query){
  if(!nodes.has(query))nodes.set(query,{
   textContent:"",innerHTML:"",href:"",style:{},dataset:{},
   classList:{toggle(){},add(){},remove(){}},
   setAttribute(){},addEventListener(){}
  });
  return nodes.get(query);
 }
 const storage=new Map([["gateCBT.realDaily.v1.2026-11-24",JSON.stringify(attempt)]]);
 const localStorage={getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)};
 const fetch=async url=>{
  const path=String(url).split("?")[0].replace(/^\.\//,"");
  const content=fs.existsSync(path)?JSON.parse(fs.readFileSync(path,"utf8")):null;
  return {ok:!!content,status:content?200:404,json:async()=>content};
 };
 const ctx=vm.createContext({
  document:{querySelector:el,querySelectorAll:()=>[]},
  window:{addEventListener(){},MathJax:null},
  localStorage,fetch,
  location:{search:"?date=2026-11-25",reload(){}},
  URLSearchParams,Intl,Date,console
 });
 // Return and await the same initializer rather than relying on timers.
 const patched=code.replace(/init\(\)\.catch\(([\s\S]*?)\);\s*$/,"globalThis.testInit=init().catch($1);");
 assert.notEqual(patched,code,"Could not capture revision initializer");
 vm.runInContext(patched,ctx,{timeout:2000});
 return {ctx,nodes,storage,el,ready:ctx.testInit};
}
const answers=Object.fromEntries(p24.questions.map(q=>[q.id,answered(q)]));
const twoNetworks=p24.questions.filter(q=>q.subject==="Network Theory").slice(0,2);
assert.equal(twoNetworks.length,2);
for(const q of twoNetworks)answers[q.id]=q.type==="MCQ"?"Z":"999999";
const attempt={submittedAt:"2026-11-24T12:00:00.000Z",paperRevisionId:p24.revisionId,answers};
const good=testEnvironment(attempt);
await good.ready;
assert(good.el("#cards").innerHTML.includes("<article class=\"card\">"),"No revision cards rendered");
assert(good.el("#cards").innerHTML.includes("15-second self-check"),"Missing recall check");
assert(good.el("#cards").innerHTML.includes("\\["),"Missing LaTeX formulas");
assert(good.el("#context").textContent.includes("2026-11-25"),"Incorrect paper date");
assert(good.el("#examLink").href.endsWith("date=2026-11-25"));
assert(good.el("#status").textContent.includes("40 scored question records"),"Did not read 40 submitted answers");
assert(good.el("#cards").innerHTML.includes("Network Theory"),"Wrong Network Theory answers did not rank for today's test");
vm.runInContext("state.reviewed.add('network-thevenin');saveReviewed();render()",good.ctx,{timeout:2000});
assert(good.storage.has("gateCBT.quickRevision.v1.2026-11-25"),"Daily progress not stored");
vm.runInContext("state.subjectMode='all';render()",good.ctx,{timeout:2000});
assert(good.el("#cards").innerHTML.includes("self-check"),"All-subject revision is empty");
// If a prior completed attempt used an older paper revision, missing changed
// source IDs must not be falsely graded as wrong or skipped.
const drift=testEnvironment({submittedAt:"2026-11-24T12:00:00Z",paperRevisionId:"outdated",answers:{[p24.questions[0].id]:answered(p24.questions[0])}});
await drift.ready;
assert(drift.el("#status").textContent.includes("1 scored question records"),"Outdated paper migration was graded as 40 questions");
assert(drift.el("#notes").innerHTML.includes("predates a paper revision"));
console.log("PASS: 29 curated packs; ranked wrong-answer revision, formulas, 15-second checks, daily progress, exam date and stale-attempt safety.");
