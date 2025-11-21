# vertex_ai_client.py
import os
import logging
from typing import Optional

MODEL_RESOURCE_DEFAULT = os.getenv("MODEL_RESOURCE", "models/2.5-flash")
PROJECT_ID = os.getenv("PROJECT_ID")
REGION = os.getenv("REGION")

# primary function to call vertex text generation
def generate_text_from_vertex(prompt: str, model_resource: Optional[str], project_id: str, region: str) -> str:
    """
    Calls Vertex AI Text Generation. Returns the model's raw text output.
    Raises if Vertex is not configured or call fails.
    """
    try:
        from google.cloud import aiplatform
    except Exception as e:
        raise RuntimeError("google-cloud-aiplatform not available") from e

    model_resource = model_resource or MODEL_RESOURCE_DEFAULT
    if not project_id or not region:
        raise RuntimeError("PROJECT_ID and REGION must be set in env for Vertex calls")

    aiplatform.init(project=project_id, location=region)
    try:
        # TextGenerationModel API (modern interface)
        model = aiplatform.TextGenerationModel.from_pretrained(model_resource)
        # Use a reasonably small token limit for SQL tasks
        response = model.predict(prompt, max_output_tokens=512)
        # response can be an object or a string
        if hasattr(response, "text"):
            return response.text
        return str(response)
    except Exception as e:
        logging.exception("Vertex predict failed")
        raise

# fallback simple rule-based generator (keeps same shape as generate_text_fallback)
def generate_text_fallback(question: str) -> dict:
    # simple rule-based JSON-like return to match nl_to_sql expected shape
    q = question.lower()
    if "duplicate" in q or "duplicates" in q:
        sql = (
            "SELECT student_id, name, age, department, attendance_percentage, internal_marks, external_marks, COUNT(*) AS duplicate_count "
            "FROM students GROUP BY student_id, name, age, department, attendance_percentage, internal_marks, external_marks HAVING COUNT(*) > 1;"
        )
        return {"sql": sql, "explain": "Find rows that are identical across all non-primary columns."}
    if "average" in q or "avg" in q:
        if "age" in q:
            col = "age"
        elif "external" in q:
            col = "external_marks"
        else:
            col = "external_marks"
        return {"sql": f"SELECT AVG({col}) AS avg_{col} FROM students;", "explain": f"Average of {col}."}
    if "summary" in q or "overview" in q:
        sql = (
            "SELECT COUNT(*) AS total_rows, "
            "AVG(age) AS avg_age, AVG(attendance_percentage) AS avg_attendance, "
            "AVG(internal_marks) AS avg_internal, AVG(external_marks) AS avg_external FROM students;"
        )
        return {"sql": sql, "explain": "Aggregated summary of the students table."}
    # default safe sample
    return {"sql": "SELECT * FROM students LIMIT 10;", "explain": "Fallback: sample rows."}
