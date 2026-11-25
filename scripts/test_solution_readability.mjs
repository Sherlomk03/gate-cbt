/**
 * Validate the CBT site's readable worked-solution presentation.
 * Uses the real solution HTML generator and original verified daily paper,
 * with no browser dependencies and without modifying exam attempts.
 */
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const html=fs.readFileSync('daily-pyq.html','utf8');
const paper=JSON.parse(fs.readFileSync('papers/daily-pyq/2026-11-25.json','utf8'));
assert.equal(paper.questions.length,40,'The original 40-question paper was changed');
const inline=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
 .map(x=>x[1]).find(s=>s.includes('function solutionHTML(q)'));
assert(inline,'Could not locate solution renderer');
new vm.Script(inline,{filename:'daily-pyq.inline.js'});
const start=inline.indexOf('function mathProse(t){');
const end=inline.indexOf('function typesetReviewMath(el){',start);
assert(start>=0&&end>start,'Solution HTML helpers were not found');
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const context=vm.createContext({esc});
vm.runInContext(inline.slice(start,end),context,{timeout:2000});
assert.equal(typeof context.solutionHTML,'function');

let formulas=0,mathDelimiters=0,nat=0,msq=0;
for(const q of paper.questions){
 const sol=q.verifiedSolution;
 assert(sol?.status==='verified'&&sol.steps?.length>=3,'Unverified or missing worked solution '+q.id);
 const output=context.solutionHTML(q);
 const count=(output.match(/class="solution-step-number"/g)||[]).length;
 assert.equal(count,sol.steps.length,'Missing solution step '+q.id);
 assert(output.includes('Step-by-step explanation'),'No derivation section: '+q.id);
 assert(output.includes('Final answer'),'Missing final-answer label: '+q.id);
 assert(output.includes(esc(q.officialKey)),'Not showing original official key '+q.id);
 assert(output.includes('solution-readable')&&output.includes('solution-concept'),'No readable structure: '+q.id);
 assert(output.includes('solution-final'),'No answer section: '+q.id);
 if(sol.mathFormula){formulas++;assert(output.includes('solution-equation'),'Math not in separate block: '+q.id);assert(output.includes('\\[')&&output.includes('\\]'),'MathJax display delimiters missing '+q.id)}
 if(output.includes('\\('))mathDelimiters++;
 if(q.type==='NAT'){nat++;assert(output.includes('Accepted numerical answer'))}
 if(q.type==='MSQ'){msq++;assert(output.includes('Correct choices'))}
}
assert(formulas>=25,'Too few equations retained');
assert(nat>0&&msq>0);
const sample=context.solutionHTML({type:'MCQ',officialKey:'A<script>',verifiedSolution:{status:'verified',concept:'a<script>',steps:['Text <img src=x onerror=alert(1)> and \\(x\\).'],reference:'<b>source</b>',mathFormula:'\\[a<b\\]'}});
assert(!sample.includes('<script>')&&!sample.includes('<img'));
assert(sample.includes('&lt;script&gt;')&&sample.includes('&lt;img'));
assert(html.includes('@media(max-width:600px)'),'No mobile layout rules');
assert(html.includes('.solution-step-text mjx-container'),'Missing inline equation overflow protection');
assert(html.includes('mathjax@3'),'MathJax script unavailable');
assert(html.includes('Print / Save as PDF'),'Print review action was removed');
assert(html.includes('renderFullReview(true)'),'The solved paper review was removed');
console.log('PASS: all 40 original GATE worked solutions rendered in readable numbered steps; '+formulas+' display formulas, '+nat+' NAT, '+msq+' MSQ; math, safety, mobile and print checks passed.');
