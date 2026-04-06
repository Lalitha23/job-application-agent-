"""
eval_classifier.py — Eval harness for the Agent 2 rejection classifier.

What this measures:
  - Precision: of emails classified as rejections, how many actually are?
  - Recall: of actual rejections, how many did we catch?
  - Extraction accuracy: when a rejection is correctly identified,
    did we extract the right Job ID and company?
  - False positive severity: failures are flagged by impact
    (critical = offer letter archived, high = interview invite archived)

Usage:
  uv run eval_classifier.py

Requires ANTHROPIC_API_KEY in environment.
Reads test cases from eval_data.json in the same directory.
Does not require Microsoft credentials — classifier only.
"""

import json
import os
import time
from pathlib import Path
from anthropic import Anthropic

# --- Config ---
EVAL_DATA_PATH = Path(__file__).parent / "eval_data.json"
MODEL = "claude-haiku-4-5-20251001"

anthropic = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# --- Classifier (with confidence field added) ---
def classify_email(subject: str, body: str) -> dict:
    """
    Classify an email as a job rejection and extract Job ID and company.
    Returns is_rejection, job_id, company, and confidence (high/medium/low).

    Confidence is used as a guardrail in production:
    low-confidence results are skipped and flagged for manual review
    rather than acted on automatically.
    """
    prompt = (
        f"Analyze this email and determine if it is a job application rejection.\n\n"
        f"Subject: {subject}\n"
        f"Body: {body}\n\n"
        f"Respond in this exact format:\n"
        f"IS_REJECTION: yes or no\n"
        f"JOB_ID: the job ID if found (e.g. JR-123456, REQ-789, #12345) or NONE if not found\n"
        f"COMPANY: the company name or NONE if not found\n"
        f"CONFIDENCE: high, medium, or low\n\n"
        f"CONFIDENCE guidelines:\n"
        f"  high   — clear rejection language, no ambiguity\n"
        f"  medium — likely a rejection but language is indirect or missing key details\n"
        f"  low    — ambiguous, could be a rejection or something else"
    )

    message = anthropic.messages.create(
        model=MODEL,
        max_tokens=120,
        messages=[{"role": "user", "content": prompt}]
    )

    response = message.content[0].text
    lines = response.strip().split("\n")
    result = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()

    return {
        "is_rejection": result.get("IS_REJECTION", "no").lower() == "yes",
        "job_id": result.get("JOB_ID", "NONE").strip(),
        "company": result.get("COMPANY", "NONE").strip(),
        "confidence": result.get("CONFIDENCE", "low").strip().lower()
    }


# --- Evaluation helpers ---
def job_id_matches(predicted: str, expected: str) -> bool:
    """
    Flexible Job ID match — handles format variation.
    Both NONE, or predicted contains expected (case-insensitive).
    """
    if expected == "NONE" and predicted == "NONE":
        return True
    if expected == "NONE" or predicted == "NONE":
        return False
    return expected.lower() in predicted.lower() or predicted.lower() in expected.lower()


def company_matches(predicted: str, expected: str) -> bool:
    """
    Flexible company match — partial match is acceptable.
    ATS emails sometimes abbreviate company names.
    """
    if expected == "NONE" and predicted == "NONE":
        return True
    if expected == "NONE" or predicted == "NONE":
        return False
    return expected.lower() in predicted.lower() or predicted.lower() in expected.lower()


SEVERITY_SYMBOL = {
    "critical": "🔴 CRITICAL",
    "high":     "🟠 HIGH    ",
    "medium":   "🟡 MEDIUM  ",
    "low":      "🟢 LOW     ",
}


# --- Main eval runner ---
def run_eval():
    test_cases = json.loads(EVAL_DATA_PATH.read_text())

    results = []
    print(f"\nRunning {len(test_cases)} test cases against {MODEL}...\n")
    print("-" * 70)

    for tc in test_cases:
        # Small delay to avoid rate limits
        time.sleep(0.5)

        predicted = classify_email(tc["subject"], tc["body"])
        expected = tc["expected"]

        # Evaluate each field
        rejection_correct = predicted["is_rejection"] == expected["is_rejection"]
        job_id_correct    = job_id_matches(predicted["job_id"], expected["job_id"])
        company_correct   = company_matches(predicted["company"], expected["company"])

        # Overall pass: rejection correct + extraction correct when is_rejection=true
        if expected["is_rejection"]:
            passed = rejection_correct and job_id_correct and company_correct
        else:
            # For non-rejections, only the is_rejection call matters —
            # extraction fields are irrelevant if we correctly skip it
            passed = rejection_correct

        results.append({
            "id": tc["id"],
            "category": tc["category"],
            "passed": passed,
            "rejection_correct": rejection_correct,
            "job_id_correct": job_id_correct,
            "company_correct": company_correct,
            "expected_is_rejection": expected["is_rejection"],
            "predicted_is_rejection": predicted["is_rejection"],
            "expected_job_id": expected["job_id"],
            "predicted_job_id": predicted["job_id"],
            "expected_company": expected["company"],
            "predicted_company": predicted["company"],
            "confidence": predicted["confidence"],
            "severity_if_wrong": tc["severity_if_wrong"],
            "subject": tc["subject"],
        })

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{tc['id']} {status}  [{tc['category']}]")

        if not passed:
            sev = SEVERITY_SYMBOL.get(tc["severity_if_wrong"], tc["severity_if_wrong"])
            print(f"       Severity : {sev}")
            if not rejection_correct:
                print(f"       is_rejection : expected={expected['is_rejection']}  got={predicted['is_rejection']}")
            if expected["is_rejection"] and not job_id_correct:
                print(f"       job_id       : expected={expected['job_id']}  got={predicted['job_id']}")
            if expected["is_rejection"] and not company_correct:
                print(f"       company      : expected={expected['company']}  got={predicted['company']}")
        else:
            print(f"       confidence={predicted['confidence']}")

    # --- Summary metrics ---
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total       = len(results)
    passed      = sum(1 for r in results if r["passed"])
    failed      = total - passed

    # Precision and recall on is_rejection
    true_rejections  = [r for r in results if r["expected_is_rejection"]]
    true_non_reject  = [r for r in results if not r["expected_is_rejection"]]

    true_positives   = sum(1 for r in true_rejections if r["predicted_is_rejection"])
    false_negatives  = sum(1 for r in true_rejections if not r["predicted_is_rejection"])
    false_positives  = sum(1 for r in true_non_reject if r["predicted_is_rejection"])
    true_negatives   = sum(1 for r in true_non_reject if not r["predicted_is_rejection"])

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall    = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"\nOverall     : {passed}/{total} passed ({100*passed//total}%)")
    print(f"Precision   : {precision:.2f}  (of emails called rejections, how many were?)")
    print(f"Recall      : {recall:.2f}  (of actual rejections, how many did we catch?)")
    print(f"F1          : {f1:.2f}")
    print(f"\nTrue positives  : {true_positives}")
    print(f"True negatives  : {true_negatives}")
    print(f"False positives : {false_positives}  ← archives something it shouldn't")
    print(f"False negatives : {false_negatives}  ← misses a rejection (less harmful)")

    # Extraction accuracy (on correctly identified rejections only)
    correctly_identified = [r for r in results if r["expected_is_rejection"] and r["predicted_is_rejection"]]
    if correctly_identified:
        job_id_acc  = sum(1 for r in correctly_identified if r["job_id_correct"]) / len(correctly_identified)
        company_acc = sum(1 for r in correctly_identified if r["company_correct"]) / len(correctly_identified)
        print(f"\nExtraction (on correctly identified rejections):")
        print(f"  Job ID accuracy  : {job_id_acc:.2f}")
        print(f"  Company accuracy : {company_acc:.2f}")

    # Confidence distribution
    conf_counts = {"high": 0, "medium": 0, "low": 0}
    for r in results:
        conf_counts[r["confidence"]] = conf_counts.get(r["confidence"], 0) + 1
    print(f"\nConfidence distribution:")
    print(f"  high   : {conf_counts.get('high', 0)}")
    print(f"  medium : {conf_counts.get('medium', 0)}")
    print(f"  low    : {conf_counts.get('low', 0)}")

    # Flag high/critical failures explicitly
    bad_failures = [
        r for r in results
        if not r["passed"] and r["severity_if_wrong"] in ("critical", "high")
    ]
    if bad_failures:
        print(f"\n⚠️  HIGH/CRITICAL failures ({len(bad_failures)}):")
        for r in bad_failures:
            sev = SEVERITY_SYMBOL.get(r["severity_if_wrong"])
            print(f"  {sev}  {r['id']} — {r['subject'][:60]}")
        print("\n  These cases must pass before deploying. A false positive here")
        print("  archives a folder the user did not intend to archive.")
    else:
        print("\n✅ No high/critical severity failures.")

    # Guidance on confidence threshold
    print(f"\nConfidence guardrail guidance:")
    print(f"  In production (watcher.py), set MIN_CONFIDENCE = 'medium'.")
    print(f"  Low-confidence results → skip archival, write to review_needed.csv.")
    print(f"  This trades recall for safety — missing a rejection is less harmful")
    print(f"  than archiving an interview invite or offer letter.")

    print("\n" + "=" * 70)
    return passed == total


if __name__ == "__main__":
    all_passed = run_eval()
    exit(0 if all_passed else 1)
