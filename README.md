# GATE 2027 CBT (PYQ-first)

A standalone browser-based question-paper interface with a date-indexed paper feed, per-paper answers, paper history, topic-wise mistakes and revision filters.

## Hosting

GitHub Pages: Settings → Pages → Source: **GitHub Actions**. Then use Actions → **Publish GATE CBT website (verified paper library)** → Run workflow (if no deployment started automatically). The project URL will be `https://sherlomk03.github.io/gate-cbt/` after successful deployment.

## Important question-source integrity

The 20 November 2026 seed paper is imported from previous ChatGPT practice and **is not independently verified against the official paper and final key in this build**. It is **not** a bank of 40 authenticated PYQs and does not carry answer keys for automatic grading. Previous practice summaries are not complete paper records. The app must not imply verified provenance for records without the official source and matched key.

**Automatic question generation is disabled.** No daily original-only generator is deployed. To add a new paper, audit each historical question against the corresponding official master paper and final key, create `papers/YYYY-MM-DD.json`, and add an entry in `papers/manifest.json`. The hosted site can then load the new paper. Automatic 8 AM IST updates require a populated audited PYQ bank and a separate scheduled selector workflow.

## Local progress and privacy

Answers and history are stored in browser localStorage for that browser and site. They are not synced across browsers/devices and do not follow automatically from a previously opened file:// version of the app. Use Settings → Download complete backup to safeguard local progress. Do not commit personal backups or API secrets to this public repository.

## Features

- 40-question, four-subject test interface with MCQ, MSQ and numerical answer controls
- Question palette, mark-for-review and subject navigation
- Per-paper browser autosave, dated history and filtering by subject/topic
- Topic-wise wrong and skipped question review where usable answer keys are present
- Date-based paper manifest for future reviewed releases

This is an initial deployment, **not** a fully automated verified-PYQ publishing service or cross-device account-backed progress service.
