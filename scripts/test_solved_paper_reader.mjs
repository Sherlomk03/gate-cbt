/**
 * Smoke-tests for the actual interactive solved-paper reader and official
 * 25-Nov source dataset. No browser extensions or external libraries needed.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const html=fs.readFileSync('solved-paper.html','utf8');
const cbt=fs.readFileSync('daily-pyq.html','utf8');
const paper=JSON.parse(fs.readFileSync('papers/daily-pyq/2026-11-25.json','utf8'));
const manifest=JSON.parse(fs.readFileSync('papers/daily-pyq/manifest.json','utf8'));
const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
const source=scripts.find(s=>s.includes('function renderSolution(q)'));
assert(source,'Could not find solution-reader logic');
new vm.Script(source,{filename:'solved-paper.html'});
assert.equal(paper.questions.length,40,'Original paper must remain unchanged');
assert(paper.questions.every(q=>q.verifiedSolution?.steps?.length>=3));
assert(html.includes('One step at a time')&&html.includes('aria-pressed'));
assert(html.includes('source-image')&&html.includes('question-rail'));
assert(html.includes('fontPlus')&&html.includes('fontMinus'));
assert(html.includes('max-width:1220px')&&html.includes('max-width:830px'));
assert(html.includes('mathjax@3'));
assert(html.includes('paperRevisionId'));
assert(html.includes('reader')&&html.includes('lightbox'));
assert(cbt.includes('href="./solved-paper.html?date='));
assert(cbt.includes('showLegacyReview'));
assert(!source.includes('localStorage.setItem('),'Study reader should never mutate exam answers');

function letterAnswer(q) {
 const key=String(q.officialKey);
 if(q.type==='MSQ')return [...new Set((key.match(/[A-D]/g)||[]))];
 if(q.type==='MCQ')return key.split(/\s+OR\s+/)[0].trim();
 const match=key.match(/-?\d+(?:\.\d+)?/);return match?match[0]:'0';
}
function mockAttempt(){
 return {submittedAt:'2026-11-25T14:32:00.000Z',paperRevisionId:paper.revisionId,
 answers:Object.fromEntries(paper.questions.filter(q=>q.officialKey!=='MTA').map(q=>[q.id,letterAnswer(q)]))};
}
function fakeUI(saved){
 const elements=new Map(),filterButtons=['all','wrong','skipped','correct'].map(filter=>({dataset:{filter},classList:{toggle(){}}}));
 function el(key){
  if(!elements.has(key))elements.set(key,{
    textContent:'',innerHTML:'',value:'',hidden:false,disabled:false,dataset:{},className:'',
    style:{display:''},classList:{toggle(){}},focus(){},scrollIntoView(){},
    setAttribute(){},getAttribute(){},
    querySelectorAll(selector){if(key==='#filters'&&selector==='button')return filterButtons;return[]}
  });
  return elements.get(key);
 }
 const dom={querySelector:el,querySelectorAll:()=>[],activeElement:null,addEventListener(){}};
 const store=new Map(saved?[['gateCBT.realDaily.v1.2026-11-25',JSON.stringify(saved)]]:[]);
 const localStorage={getItem:k=>store.get(k)||null};
 const fetch=async u=>{
   const url=String(u);const data=url.includes('manifest.json')?manifest:url.includes('2026-11-25.json')?paper:null;
   return {ok:!!data,status:data?200:404,json:async()=>data};
 };
 const location={href:'https://sherlomk03.github.io/gate-cbt/solved-paper.html?date=2026-11-25',search:'?date=2026-11-25'};
 const history={replaceState(){}};
 const window={innerWidth:1450,MathJax:{typesetPromise:()=>Promise.resolve()}};
 const code=source.replace(/init\(\);\s*$/,'window.__initPromise=init();');
 assert.notEqual(code,source,'Init hook not found');
 const context=vm.createContext({document:dom,window,localStorage,fetch,location,history,URL,URLSearchParams,Intl,Date,console});
 vm.runInContext(code,context,{timeout:3000});
 return {context,elements,el,window,filterButtons,ready:window.__initPromise,store};
}
const blocked=fakeUI(null);
await blocked.ready;
assert.equal(blocked.el('#reader').hidden,true,'Solutions must stay locked before submission');
assert(blocked.el('#message').innerHTML.includes('Finish the paper first'),'Missing pre-submission guard');

const scored=fakeUI(mockAttempt());
await scored.ready;
assert.equal(scored.el('#reader').hidden,false,'Submitted result must unlock study reader');
assert(scored.el('#scoreValues').innerHTML.includes('Final score'));
assert(scored.el('#questionMedia').innerHTML.includes('source-image'));
assert(scored.el('#solutionBody').innerHTML.includes('The derivation'));
assert(scored.el('#solutionBody').innerHTML.includes('math-display'));
assert(scored.el('#solutionBody').innerHTML.includes('OFFICIAL ANSWER'));
assert(scored.el('#solutionBody').innerHTML.includes('class="step'));
assert(scored.el('#paperLinks').innerHTML.includes('Original paper'));
assert(scored.el('#rail').innerHTML.includes('Question'));
assert(scored.el('#answerComparison').innerHTML.includes('YOUR ANSWER'));
const stat=vm.runInContext('state.rows.map(x=>x.r.status)',scored.context);
assert.equal(stat.length,40);
assert.equal(stat.filter(s=>s==='wrong').length,0,'Mock right answers should be graded correct');
assert(!scored.store.has('gateCBT.realDaily.v1.2026-11-25.changes'),'Reader changed exam storage');

// Check that clicking progressive-mode and revealing a step does not modify saved answers.
scored.el('#stepMode').onclick();
assert(scored.el('#solutionBody').innerHTML.includes('hidden-step'));
scored.el('#revealNext').onclick();
assert(scored.el('#solutionBody').innerHTML.includes('Reveal next step'));
scored.el('#showAll').onclick();
assert(!scored.el('#solutionBody').innerHTML.includes('hidden-step'));

// Check 40 original mathematical explanations have a displayed equation when available.
let formulas=0,allSteps=0;
for(const q of paper.questions){
 vm.runInContext('state.stepMode=false',scored.context);
 scored.context.renderSolution(q);
 const out=scored.el('#solutionBody').innerHTML;
 const steps=(out.match(/class="step"/g)||[]).length;
 assert.equal(steps,q.verifiedSolution.steps.length,'Missing a reasoning step in '+q.id);
 assert(out.includes('OFFICIAL ANSWER'),'Missing answer label in '+q.id);
 allSteps+=steps;
 if(q.verifiedSolution.mathFormula){formulas++;assert(out.includes('math-card'),'Missing equation card in '+q.id)}
}
assert(formulas>=35,'Display math was unexpectedly removed');
assert(allSteps>=130,'A significant number of worked steps were lost');

// Paper revision mismatch must never be graded against the wrong question set.
if(paper.revisionId){
 const stale=fakeUI({...mockAttempt(),paperRevisionId:'different-revision'});
 await stale.ready;
 assert.equal(stale.el('#reader').hidden,true);
 assert(stale.el('#message').innerHTML.includes('Paper version changed'));
}
console.log('PASS: focused GATE solution reader; '+paper.questions.length+' questions, '+allSteps+' explanatory steps, '+formulas+' equations; filtering, study controls, read-only results, source images, and submission gates.');
