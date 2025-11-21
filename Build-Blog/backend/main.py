# main.py
import os
import json
import tempfile
import logging
import traceback
from flask import Flask, request, jsonify
from dotenv import load_dotenv

import pandas as pd
import numpy as np

from gcp_helpers import (
    upload_file_to_gcs,
    download_blob_to_file,
    run_bigquery,
    run_cloudsql_query,
)
from analysis_utils import summarize_dataframe
from nl_to_sql import nl_to_sql  # LLM wrapper (uses Vertex)

load_dotenv()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET = os.getenv("BUCKET_NAME")
INSTANCE = os.getenv("INSTANCE_CONNECTION_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

# ------- helpers -------
def sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.replace([np.inf, -np.inf], np.nan)
    return df

def load_df_any(path_or_bytes):
    if isinstance(path_or_bytes, (bytes, bytearray)):
        raw = path_or_bytes
        from io import BytesIO
        # try csv
        try:
            return pd.read_csv(BytesIO(raw))
        except Exception:
            pass
        # try excel
        try:
            return pd.read_excel(BytesIO(raw))
        except Exception:
            pass
        # try json
        try:
            data = json.loads(raw.decode("utf-8"))
            return pd.DataFrame(data)
        except Exception:
            pass
        raise Exception("Unsupported file format (bytes).")
    else:
        # path
        with open(path_or_bytes, "rb") as f:
            return load_df_any(f.read())

# ------- endpoints -------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/upload", methods=["POST"])
def upload():
    try:
        # JSON body mode
        if request.is_json:
            body = request.get_json(force=True)
            if "data" not in body:
                return jsonify({"error": "Missing data"}), 400
            df = pd.DataFrame(body["data"])
            df = sanitize_df(df)
            gcs_path = None
            if BUCKET:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
                df.to_json(tmp.name, orient="records")
                gcs_path = upload_file_to_gcs(tmp.name, BUCKET, f"upload-{os.urandom(6).hex()}.json")
            summary, charts = summarize_dataframe(df)
            return jsonify({"summary": summary, "charts": charts, "gcs_path": gcs_path})
        # multipart file mode
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400
        file = request.files["file"]
        raw = file.read()
        df = load_df_any(raw)
        df = sanitize_df(df)
        gcs_path = None
        if BUCKET:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=file.filename)
            with open(tmp.name, "wb") as f:
                f.write(raw)
            gcs_path = upload_file_to_gcs(tmp.name, BUCKET, file.filename)
        summary, charts = summarize_dataframe(df)
        return jsonify({"summary": summary, "charts": charts, "gcs_path": gcs_path})
    except Exception as e:
        logging.exception("UPLOAD ERROR")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/summarize", methods=["POST"])
def summarize():
    try:
        body = request.get_json(force=True)
        if "data" in body:
            df = pd.DataFrame(body["data"])
        elif "gcs_path" in body:
            tmp = tempfile.NamedTemporaryFile(delete=False)
            download_blob_to_file(body["gcs_path"], tmp.name)
            df = load_df_any(tmp.name)
        else:
            return jsonify({"error": "Provide data or gcs_path"}), 400
        df = sanitize_df(df)
        summary, charts = summarize_dataframe(df)
        return jsonify({"summary": summary, "charts": charts})
    except Exception as e:
        logging.exception("SUMMARIZE ERROR")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/nl_query_file", methods=["POST"])
def nl_query_file():
    try:
        body = request.get_json(force=True)
        question = body.get("question")
        data = body.get("data")
        gcs_path = body.get("gcs_path")
        if not question:
            return jsonify({"error": "Missing question"}), 400
        if data:
            df = pd.DataFrame(data)
        elif gcs_path:
            tmp = tempfile.NamedTemporaryFile(delete=False)
            download_blob_to_file(gcs_path, tmp.name)
            df = load_df_any(tmp.name)
        else:
            return jsonify({"error": "Provide data or gcs_path"}), 400
        df = sanitize_df(df)
        q = question.lower()
        if "summarize" in q or "overview" in q:
            summary, charts = summarize_dataframe(df)
            return jsonify({"summary": summary, "charts": charts})
        if "head" in q or "first" in q:
            return jsonify({"summary": {"head": df.head(10).to_dict(orient='records')}, "charts": []})
        # Fallback: we will ask the LLM to operate on the file-level question (but here we return summary)
        summary, charts = summarize_dataframe(df)
        return jsonify({"summary": summary, "charts": charts})
    except Exception as e:
        logging.exception("NL_FILE ERROR")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/debug_sql", methods=["POST"])
def debug_sql():
    try:
        body = request.get_json(force=True)
        question = body.get("question")
        if not question:
            return jsonify({"error": "Missing question"}), 400
        sql = nl_to_sql(question)
        # Attempt to parse JSON if nl_to_sql returned JSON wrapper
        if isinstance(sql, dict) and sql.get("sql"):
            return jsonify({"sql": sql.get("sql")}), 200
        return jsonify({"sql": str(sql)}), 200
    except Exception as e:
        logging.exception("DEBUG_SQL ERROR")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/nl_query_db", methods=["POST"])
def nl_query_db():
    try:
        body = request.get_json(force=True)
        question = body.get("question")
        target = body.get("target", "cloudsql")
        if not question:
            return jsonify({"error": "Missing question"}), 400

        # Generate SQL via nl_to_sql
        sql_resp = nl_to_sql(question)
        # nl_to_sql returns JSON-like dict or string. Normalize:
        if isinstance(sql_resp, dict):
            sql = sql_resp.get("sql", "").strip()
            extra = sql_resp.get("explain")
        else:
            sql = str(sql_resp).strip()
            extra = None

        # sanitize code fences
        sql = sql.replace("```sql", "").replace("```", "").strip()
        logging.info("Generated SQL: %s", sql)

        # simple protection
        destructive_tokens = ["drop ", "truncate ", "alter "]
        if any(tok in sql.lower() for tok in destructive_tokens):
            return jsonify({"error": "Rejected SQL: destructive statement detected", "sql": sql}), 400

        if target == "bigquery":
            try:
                rows = run_bigquery(PROJECT_ID, sql)
            except Exception as e:
                logging.exception("BigQuery execution failed")
                return jsonify({"error": "BigQuery execution failed", "sql": sql, "details": str(e), "trace": traceback.format_exc()}), 500
        else:
            cfg = {
                "instance_connection_name": INSTANCE,
                "db_name": DB_NAME,
                "user": DB_USER,
                "password": DB_PASS,
            }
            try:
                rows = run_cloudsql_query(sql, cfg)
            except Exception as e:
                logging.exception("CloudSQL execution failed")
                return jsonify({"error": "CloudSQL execution failed", "sql": sql, "details": str(e), "trace": traceback.format_exc()}), 500

        out = {"sql": sql, "rows": rows}
        if extra:
            out["explain"] = extra
        return jsonify(out), 200

    except Exception as e:
        logging.exception("NL_DB ERROR")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
