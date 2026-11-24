#!/usr/bin/env python3
"""Fail-closed checks for the subject taxonomy used by daily GATE EE/EC CBT papers.
Only source-audited or context-screened subjects are eligible for selection.
This script never rewrites question IDs, answers, or existing attempts.
"""
import json
import pathlib
import re
from collections import Counter

BANK=pathlib.Path("pyq/five-years")
DAILY=pathlib.Path("papers/daily-pyq")
MATH_GUARD=re.compile(
    r"standing wave ratio|economic dispatch|generator buses|nominal.π model|"
    r"nominal.pi model|transmission line|\bpower system\b|\bpower network\b|"
    r"\bthevenin\b|\bload flow\b",re.I
)

def main():
    papers=sorted(BANK.glob("20??-??.json"))
    assert len(papers)==10, f"Expected ten 2022–2026 EE/EC source papers, got {len(papers)}"
    bank={}
    for path in papers:
        obj=json.loads(path.read_text(encoding="utf-8"))
        qs=obj["questions"]
        assert len(qs)==65, path
        for q in qs:
            assert q["id"] not in bank, q["id"]
            bank[q["id"]]=q
            if q["number"]<=10:
                assert q["section"]=="GA",q["id"]
                continue
            assert q.get("subject") and q.get("topic"),q["id"]
            assert q.get("officialKey") and q.get("imagePath"),q["id"]
            assert q.get("taxonomyReviewStatus"),q["id"]
            assert isinstance(q.get("selectionEligible"),bool),q["id"]
            if q["selectionEligible"]:
                assert q["taxonomyReviewStatus"] in (
                    "source_text_audited","source_text_curated","automatic_context_match"
                ),q["id"]
                if q["taxonomyReviewStatus"]=="automatic_context_match":
                    assert q.get("classificationStatus")=="high_auto",q["id"]
                if q["subject"]=="Engineering Mathematics":
                    assert not MATH_GUARD.search((q.get("sourceExtract") or "")[:480]),(
                        "Wrong-subject math PYQ",q["id"])
    assert len(bank)==650
    # Only explicitly audited historical questions are eligible for daily use.
    # Key and crop checks are performed against the locked official-source record.
    VERIFIED=pathlib.Path("pyq/historical/verified")
    for path in sorted(VERIFIED.glob("20??-??*.json")):
        paper=json.loads(path.read_text(encoding="utf-8"))
        assert paper["verificationStatus"]=="question_level_official_key_and_image_audited",path
        assert paper["paperUrl"] and paper["keyUrl"],path
        assert paper["imageBase"]=="./pyq/historical/",path
        for q in paper["questions"]:
            assert q["id"] not in bank,q["id"]
            assert q["year"]==paper["year"] and q["branch"]==paper["branch"],q["id"]
            assert q["section"]==paper["branch"],q["id"]
            assert q["id"].startswith(f'{paper["year"]}-{paper["branch"]}-S'),q["id"]
            assert all(q.get(k) is True for k in ("sessionVerified","keyVerifiedForQuestion",
                        "imageCropReviewed","selectionEligible")),q["id"]
            assert q["subject"]!="Unclassified" and q["topic"],q["id"]
            assert q["type"] in ("MCQ","MSQ","NAT"),q["id"]
            assert q["officialKey"] and q["officialKey"]!="MTA",q["id"]
            assert (VERIFIED.parent/q["imagePath"]).is_file(),q["id"]
            bank[q["id"]]=q
    summary=json.loads((BANK/"taxonomy-summary.json").read_text(encoding="utf-8"))
    assert summary["technicalQuestions"]==550
    assert summary["changedSubjectCount"]==44
    assert summary["eligibleForDaily"]==sum(
        q.get("selectionEligible") is True for q in bank.values()
    )
    for correction in summary["subjectCorrections"]:
        actual=bank[correction["id"]]
        assert actual["subject"]==correction["to"],correction["id"]
        assert actual["reclassifiedFrom"]==correction["from"],correction["id"]

    for path in sorted(DAILY.glob("20??-??-??.json")):
        paper=json.loads(path.read_text(encoding="utf-8"))
        qs=paper["questions"]
        assert len(qs)==40 and len(set(q["id"] for q in qs))==40,path
        for q in qs:
            if q.get("sourceType")=="ace_classroom":
                assert q.get("officialGatePYQ") is False,q["id"]
                continue
            original=bank[q["id"]]
            assert q["subject"]==original["subject"],(
                "Daily paper has old subject category",str(path),q["id"])
            assert q["officialKey"]==original["officialKey"],(
                "Answer key mismatch",str(path),q["id"])
        if paper.get("taxonomyCorrectedAt"):
            assert sum(paper["actualSubjectCounts"].values())==40,path
        else:
            assert all(Counter(q["subject"] for q in qs)[sub]==10
                       for sub in paper["subjects"]),path
            assert all(q.get("sourceType")=="ace_classroom"
                       or q.get("selectionEligibleForFuture") is not False
                       for q in qs),path
    print("PASS: 550 technical PYQs screened; 44 curated subject fixes; "
          "every daily question uses the corrected category; math guard active.")

if __name__=="__main__":
    main()
