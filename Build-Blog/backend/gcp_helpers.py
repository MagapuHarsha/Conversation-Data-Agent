# gcp_helpers.py
import logging
from google.cloud import storage, bigquery
from google.cloud.sql.connector import Connector
import pymysql

logger = logging.getLogger(__name__)
storage_client = storage.Client()

def upload_file_to_gcs(local_path: str, bucket_name: str, dest_blob_name: str) -> str:
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(dest_blob_name)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{dest_blob_name}"

def download_blob_to_file(gcs_path: str, local_path: str):
    assert gcs_path.startswith("gs://"), "gcs_path must start with gs://"
    parts = gcs_path[5:].split("/", 1)
    bucket_name = parts[0]
    blob_name = parts[1] if len(parts) > 1 else ""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(local_path)

def run_bigquery(project_id: str, sql: str):
    client = bigquery.Client(project=project_id)
    query_job = client.query(sql)
    results = [dict(row) for row in query_job.result()]
    return results

def run_cloudsql_query(sql: str, db_config: dict):
    connector = None
    conn = None
    try:
        connector = Connector()
        conn = connector.connect(
            db_config["instance_connection_name"],
            "pymysql",
            user=db_config["user"],
            password=db_config["password"],
            db=db_config["db_name"],
        )
        with conn.cursor() as cursor:
            cursor.execute(sql)
            cols = [col[0] for col in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
        return [dict(zip(cols, r)) for r in rows]
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            logger.exception("Failed to close DB connection")
        try:
            if connector:
                connector.close()
        except Exception:
            logger.exception("Failed to close connector")
