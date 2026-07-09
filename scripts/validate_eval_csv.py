import dotenv
import os
dotenv.load_dotenv(os.getenv("ENV_FILE", ".env"))

import csv
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

from src.app.config import settings

CSV_PATH = Path(__file__).parent.parent / "eval" / "eval_questions.csv"
sync_engine = create_engine(settings.sync_database_url)

VALID_CATEGORIES = {"sql_only", "rag_only", "hybrid"}


def main():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    errors = []

    for row in rows:
        rid = row.get("id", "?")
        category = row.get("category", "").strip()
        question = row.get("question", "").strip()
        expected_facts = row.get("expected_facts", "").strip()
        ground_truth_sql = row.get("ground_truth_sql", "").strip()

        # 1. Category sanity
        if category not in VALID_CATEGORIES:
            errors.append(f"Row {rid}: invalid category '{category}'")

        # 2. Every row needs a question
        if not question:
            errors.append(f"Row {rid}: empty question")

        # 3. rag_only should NEVER have ground_truth_sql filled
        if category == "rag_only" and ground_truth_sql:
            errors.append(f"Row {rid} [rag_only]: ground_truth_sql should be empty, found: {ground_truth_sql[:60]!r}")

        # 4. sql_only/hybrid should generally HAVE ground_truth_sql
        #    (soft warning, not a hard error — some might be legitimately qualitative)
        if category in ("sql_only", "hybrid") and not ground_truth_sql and not expected_facts:
            errors.append(f"Row {rid} [{category}]: has NEITHER ground_truth_sql NOR expected_facts — nothing to grade against")

        # 5. If ground_truth_sql is present, verify it's actually valid, executable SQL
        if ground_truth_sql:
            if not ground_truth_sql.lower().strip().startswith("select"):
                errors.append(f"Row {rid}: ground_truth_sql doesn't start with SELECT — likely plain text, not SQL: {ground_truth_sql[:60]!r}")
            else:
                try:
                    with sync_engine.connect() as conn:
                        conn.execute(text(ground_truth_sql))
                except ProgrammingError as e:
                    errors.append(f"Row {rid}: ground_truth_sql failed to execute — {str(e).splitlines()[0]}")
                except Exception as e:
                    errors.append(f"Row {rid}: unexpected error running ground_truth_sql — {e}")

        # 6. hybrid rows should have BOTH expected_facts AND ground_truth_sql
        #    since a hybrid answer needs both halves checked
        if category == "hybrid" and (not expected_facts or not ground_truth_sql):
            missing = []
            if not expected_facts:
                missing.append("expected_facts")
            if not ground_truth_sql:
                missing.append("ground_truth_sql")
            errors.append(f"Row {rid} [hybrid]: missing {', '.join(missing)} — hybrid rows need both to properly grade")

    print(f"Checked {len(rows)} rows.\n")
    if errors:
        print(f"❌ Found {len(errors)} issue(s):\n")
        for e in errors:
            print(f"  - {e}")
    else:
        print("✅ No issues found — CSV is clean.")


if __name__ == "__main__":
    main()