# nl_to_sql.py
import os
import json
import logging
from typing import Union

from vertex_ai_client import generate_text_from_vertex, generate_text_fallback

# Use the schema you provided. Update if schema changes.
SCHEMA = {
    "table": "students",
    "columns": [
        {"name": "student_id", "type": "INT"},
        {"name": "name", "type": "VARCHAR"},
        {"name": "age", "type": "INT"},
        {"name": "department", "type": "VARCHAR"},
        {"name": "attendance_percentage", "type": "INT"},
        {"name": "internal_marks", "type": "INT"},
        {"name": "external_marks", "type": "INT"}
    ]
}

MODEL_RESOURCE = os.getenv("MODEL_RESOURCE", "models/2.5-flash")  # default to 2.5 flash
PROJECT_ID = os.getenv("PROJECT_ID")
REGION = os.getenv("REGION")

# Strong instruction: output JSON only
PROMPT = """
You are an expert SQL generator for MySQL 8 (Cloud SQL). Use this schema:

Table: {table}
Columns:
{columns}

INSTRUCTIONS:
1) Output ONLY valid JSON with this exact shape:
   {{
     "sql": "<SQL statement>",
     "explain": "<short explanation in one sentence (optional)>"
   }}
2) SQL must be valid MySQL 8 syntax.
3) Use the table and column names exactly as provided.
4) Do NOT output any extra text outside the JSON.
5) If question is ambiguous, pick the most useful aggregation or sample (explain why in the explain field).
6) Avoid destructive statements (DROP/ALTER/TRUNCATE/DELETE) — prefer SELECT.
7) For summary-like questions, return an aggregated summary query (counts/averages).
8) For "count duplicates" interpret as rows with identical values across all non-primary columns unless user specifies columns.

User question:
"{question}"
"""

# If model response is not JSON or contains extra text, we retry once with a stricter prompt.
RETRY_PROMPT = PROMPT + "\nRETRY: Respond ONLY with a valid JSON object and nothing else."

def _format_schema() -> str:
    lines = []
    for c in SCHEMA["columns"]:
        lines.append(f"- {c['name']} ({c['type']})")
    return "\n".join(lines)

def nl_to_sql(question: str) -> Union[str, dict]:
    prompt = PROMPT.format(table=SCHEMA["table"], columns=_format_schema(), question=question)
    try:
        resp = generate_text_from_vertex(prompt, MODEL_RESOURCE, PROJECT_ID, REGION)
        # model should return JSON string. Try parse.
        try:
            parsed = json.loads(resp)
            if isinstance(parsed, dict) and parsed.get("sql"):
                return parsed
            # if parsed is not dict, fallback to retry
        except Exception:
            # try to strip surrounding text and find JSON object
            try:
                start = resp.find("{")
                end = resp.rfind("}")
                if start != -1 and end != -1:
                    candidate = resp[start:end+1]
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict) and parsed.get("sql"):
                        return parsed
            except Exception:
                pass
        # Retry once with stricter instruction
        resp2 = generate_text_from_vertex(RETRY_PROMPT.format(table=SCHEMA["table"], columns=_format_schema(), question=question), MODEL_RESOURCE, PROJECT_ID, REGION)
        try:
            parsed2 = json.loads(resp2)
            if isinstance(parsed2, dict) and parsed2.get("sql"):
                return parsed2
        except Exception:
            pass
    except Exception as e:
        logging.exception("Vertex failed: %s", e)

    # Final fallback: rule-based generator
    return generate_text_fallback(question)
