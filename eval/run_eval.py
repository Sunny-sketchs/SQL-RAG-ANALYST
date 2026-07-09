import dotenv
import os
dotenv.load_dotenv(os.getenv("ENV_FILE", ".env"))

import re
import csv
import json
import asyncio
from datetime import date
from pathlib import Path

from decimal import Decimal
from numbers import Real
import httpx
from openai import AsyncOpenAI
from sqlalchemy import create_engine, text

from src.app.config import settings

API_URL = "http://127.0.0.1:8000/ask"
QUESTIONS_PATH = Path(__file__).parent / "eval_questions.csv"
RESULTS_DIR = Path(__file__).parent / "results"

EXPECTED_ROUTE = {"sql_only": "sql", "rag_only": "rag", "hybrid": "hybrid"}

grader_client = AsyncOpenAI(api_key=settings.openai_api_key)
sync_engine = create_engine(settings.sync_database_url)

GRADER_PROMPT = """Question: {question}
Expected fact: {expected_facts}
Actual answer: {answer}

Does the actual answer correctly convey the expected fact? Reply with exactly
one word: yes or no."""


def get_ground_truth(sql: str):
    """Run ground-truth SQL directly — could return a number or a string."""
    with sync_engine.connect() as conn:
        return conn.execute(text(sql)).scalar()


def extract_numbers(text_str: str) -> list[float]:
    """Extract all numeric values from text, handling commas and negatives."""
    cleaned = text_str.replace(",", "")
    matches = re.findall(r"-?\d+\.?\d*", cleaned)
    return [float(m) for m in matches if m not in ("", "-", ".")]


def value_match(answer: str, expected, tolerance: float = 0.5) -> bool:
    """Compare an LLM's answer text against a ground-truth value from the DB.
    Handles int, float, Decimal (all numeric types Postgres/psycopg2 can
    return), plain strings, and None (missing/empty ground truth)."""

    if expected is None:
        return False  # no ground truth to check against — always fail loudly, don't silently pass

    # bool is technically a subclass of int in Python — exclude it explicitly
    # so a boolean ground truth (if ever added) isn't mistreated as numeric.
    if isinstance(expected, bool):
        return str(expected).lower() in answer.lower()

    if isinstance(expected, (int, float, Decimal, Real)):
        expected_float = float(expected)
        found = extract_numbers(answer)
        return any(abs(n - expected_float) <= tolerance for n in found)

    if isinstance(expected, str):
        return expected.strip().lower() in answer.lower()

    # Defensive fallback — if get_ground_truth() ever returns something
    # unexpected (e.g. a date, a list), fail explicitly rather than crash,
    # and this is visible in the eval report as a real gap to investigate.
    return False


async def grade_qualitative(question: str, expected_facts: str, answer: str) -> bool:
    prompt = GRADER_PROMPT.format(question=question, expected_facts=expected_facts, answer=answer)
    response = await grader_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=3,
    )
    return "yes" in response.choices[0].message.content.strip().lower()


async def run_one(client: httpx.AsyncClient, row: dict) -> dict:
    question = row["question"]
    category = row["category"]
    expected_facts = row["expected_facts"].strip()
    ground_truth_sql = row.get("ground_truth_sql", "").strip()

    try:
        resp = await client.post(API_URL, json={"query": question}, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"id": row["id"], "category": category, "question": question,
                "passed": False, "error": str(e), "route": None, "answer": None}

    answer = data.get("answer", "")
    actual_route = data.get("route", "")
    expected_route = EXPECTED_ROUTE.get(category)
    route_ok = (actual_route == expected_route)

    numeric_ok = True
    qualitative_ok = True
    notes = []

    if ground_truth_sql:
        expected_value = get_ground_truth(ground_truth_sql)
        numeric_ok = value_match(answer, expected_value) if expected_value is not None else False
        notes.append(f"ground_truth={expected_value}, found_in_answer={extract_numbers(answer) if isinstance(expected_value, (int, float)) else 'n/a'}")

    if expected_facts:
        qualitative_ok = await grade_qualitative(question, expected_facts, answer)
        notes.append(f"qualitative={'ok' if qualitative_ok else 'FAILED'}")

    content_ok = numeric_ok and qualitative_ok

    return {
        "id": row["id"], "category": category, "question": question,
        "expected_route": expected_route, "actual_route": actual_route, "route_ok": route_ok,
        "content_ok": content_ok, "grader_note": " | ".join(notes),
        "passed": route_ok and content_ok, "answer": answer,
    }


async def main():
    with open(QUESTIONS_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    async with httpx.AsyncClient() as client:
        results = []
        for row in rows:
            print(f"Running #{row['id']} [{row['category']}]: {row['question'][:60]}...")
            result = await run_one(client, row)
            results.append(result)
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"  {status} — route: {result.get('actual_route')} — {result.get('grader_note', result.get('error', ''))}")

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    by_category = {}
    for r in results:
        cat = r["category"]
        by_category.setdefault(cat, {"total": 0, "passed": 0})
        by_category[cat]["total"] += 1
        if r["passed"]:
            by_category[cat]["passed"] += 1

    summary = {"date": str(date.today()), "total": total, "passed": passed,
               "accuracy": round(passed / total, 3) if total else 0,
               "by_category": by_category, "results": results}

    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / f"eval_report_{date.today()}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'=' * 50}")
    print(f"TOTAL: {passed}/{total} passed ({summary['accuracy']:.0%})")
    for cat, stats in by_category.items():
        print(f"  {cat}: {stats['passed']}/{stats['total']}")
    print(f"Report written to: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())