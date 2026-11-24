# GATE EE/EC historical sources, 2010–2026

This archive serves the **authentic-PYQ-first** daily CBT at [daily-pyq.html](../../daily-pyq.html). It is an import *staging* and provenance system, not a claim that all historical questions have been converted into individually gradeable CBT items.

## Requested coverage
- EC papers **2010–2026**: Analog Electronics, Digital Electronics, Signals & Systems, Control Systems, Network Theory, and Engineering Mathematics.
- EE papers **2010–2026**: Engineering Mathematics (only).
- For daily Mathematics, **Linear Algebra, Probability and Statistics, Complex Variables** only, until the learner changes this.
- General Aptitude is excluded. Control Systems is **collected** here but currently excluded from the daily technical test, per the existing scheduling constraints.
- User-supplied ACE classroom Signals questions are a separately labeled source; never pass them off as original GATE or use official-key language for ACE independently derived answers.

## Files
- `source-catalog-2010-2026.json`: 34 year/branch source entries, with independently checked paper URLs vs **candidates** and key provenance.
- `staging/`: official paper image page index and parsed key inventories for those papers whose official PDFs are accessible (staged material is **not CBT eligible**).
- `source-pages/`: source PDF page images where already staged; preserve full diagrams and option lists.
- `../five-years/`: the currently active 2022–2026 historical EE/EC paper bank with individual question crops; subject/topic assignments are provisional.

## Quality gate for each 2010–2021 question
1. Confirm the paper PDF came from the organizing institute's official archive and record its source URL/hash.
2. Identify exact **year, branch, session/shift, booklet/code, section and question number**. Early years have GA at the end; recent years differ in numbering.
3. Locate exact original question (and all subparts, diagrams, options) in the PDF and render an individual readable source image; manually inspect crop boundaries.
4. Match the correct **official key**, accounting for MCQ, MSQ, NAT, marks-to-all, changed/ambiguous options, and session-specific keys. Do not use unofficial model-generated keys.
5. Audit the question's subject/topic *against source image*. Set eligibility only after key, image, numbering, and syllabus pass. Mark any unresolved question as excluded.
6. Track question IDs consistently (e.g. `2016-EC-S2-Q17` for multiple sessions) and compare against all previously published dates to avoid repeats.
7. The daily generator continues to use only eligible sources. Source-link discovery alone **must never change the number of available CBT questions**.

## GitHub Actions
- `Verify Historical GATE EE-EC Official Paper Sources` probes links and updates catalog only. Some older IIT Kanpur source hosts are not reachable from GitHub Actions.
- `Stage GATE 2019–2021 Source Pages and Key Inventories` stages official page images and key rows, with `selectionEligible=false`. It does **not** add guessed daily questions.
- Existing daily-publisher workflow remains active and prepublishes the current day plus 3 future dates because GitHub cron may be delayed.
- The historical archive browser is at `historical-papers.html` (linked from `pyq-library.html`).

## Source availability notes
The official GATE 2026 download page exposes year-wise EE/EC PDFs and associated answer keys for 2021–2025 and a historical bulk folder back to 2007. The 2026 page has master EE/EC papers and keys. An IIT Kanpur GATE 2023 mirror contains earlier-year PDFs, but GitHub Actions may be unable to resolve it. If an official answer key cannot be matched, retain the PDF for study but do not claim official grading.
