import streamlit as st
import requests
import json
import pandas as pd

# ---------------------------------------------------------
# HARD-CODE YOUR BACKEND URL
# ---------------------------------------------------------
BACKEND = ""


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def api_post(endpoint: str, data=None, files=None):
    url = BACKEND + endpoint
    try:
        if files:
            resp = requests.post(url, files=files)
        else:
            resp = requests.post(url, json=data)

        if resp.status_code != 200:
            return None, f"{resp.status_code}: {resp.text}"
        return resp.json(), None
    except Exception as e:
        return None, str(e)


def show_summary_block(summary):
    st.subheader("📊 Data Summary")

    st.write("**Shape:**", summary.get("shape"))
    st.write("**Columns:**")
    st.json(summary.get("columns"))
    st.write("**Missing Values:**")
    st.json(summary.get("missing_values"))
    st.write("**Numeric Stats:**")
    st.json(summary.get("numeric_stats"))
    st.write("**Categorical Stats:**")
    st.json(summary.get("categorical_stats"))
    st.write("**Correlation Matrix:**")
    st.json(summary.get("correlation_matrix"))
    st.write("**Data Sample:**")
    st.json(summary.get("sample"))
    st.write("**Insights:**")
    st.json(summary.get("insights"))
    st.write("**Data Quality Score:**", summary.get("data_quality_score"))


def show_charts(charts):
    if not charts:
        return
    st.subheader("📈 Charts")
    for c in charts:
        st.write(f"### {c['column']} ({c['type']})")
        st.image(c["data_uri"])


# ---------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------
st.title("🧠 Data Agent – Full Data Explorer & NL → SQL")


# =========================================================
# 1) FILE UPLOAD SECTION
# =========================================================
st.header("📁 Upload Data")

uploaded_file = st.file_uploader(
    "Upload CSV, Excel, or JSON",
    type=["csv", "xlsx", "xls", "json"]
)

if uploaded_file:
    st.success("File uploaded. Processing…")

    # -----------------------------------------------------
    # SEND FILE TO BACKEND
    # -----------------------------------------------------
    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
    resp, err = api_post("/upload", files=files)

    if err:
        st.error(f"Backend Error: {err}")
    else:
        summary = resp.get("summary")
        charts = resp.get("charts")
        gcs_path = resp.get("gcs_path")

        st.session_state["file_summary"] = summary
        st.session_state["file_charts"] = charts
        st.session_state["gcs_path"] = gcs_path

        # -------------------------------------------------
        # NEW ⭐: Store actual dataframe rows (for NL queries)
        # -------------------------------------------------
        try:
            ext = uploaded_file.name.split(".")[-1].lower()
            if ext == "csv":
                df = pd.read_csv(uploaded_file)
            elif ext in ["xlsx", "xls"]:
                df = pd.read_excel(uploaded_file)
            elif ext == "json":
                df = pd.read_json(uploaded_file)
            else:
                df = None

            if df is not None:
                st.session_state["file_data_rows"] = df.to_dict(orient="records")

        except Exception as e:
            st.error(f"Failed to parse file locally: {e}")

        # -------------------------------------------------
        show_summary_block(summary)
        show_charts(charts)


# =========================================================
# 2) FULL SUMMARY REFRESH
# =========================================================
if "file_summary" in st.session_state:
    st.header("📊 Full Summary")
    if st.button("Refresh Summary"):
        payload = {"gcs_path": st.session_state["gcs_path"]}
        resp, err = api_post("/summarize", data=payload)

        if err:
            st.error(f"Backend Error: {err}")
        else:
            show_summary_block(resp["summary"])
            show_charts(resp["charts"])


# =========================================================
# 3) NL → SQL on FILE (FIXED)
# =========================================================
if "file_summary" in st.session_state:
    st.header("💬 Ask About File")

    q = st.text_input("Ask a question about the uploaded file")

    if st.button("Run File Query"):
        if not q.strip():
            st.warning("Please enter a question.")
        else:
            payload = {
                "question": q,

                # ⭐ ALWAYS send actual file rows so backend never errors
                "data": st.session_state.get("file_data_rows"),

                # Fallback if backend still wants gcs_path
                "gcs_path": st.session_state.get("gcs_path")
            }

            resp, err = api_post("/nl_query_file", data=payload)
            if err:
                st.error(f"Backend Error: {err}")
            else:
                st.subheader("File Query Result")
                st.json(resp)


# =========================================================
# 4) NL → SQL FOR CLOUD SQL
# =========================================================
st.header("🗄️ Natural Language → SQL (CloudSQL)")

q2 = st.text_input("Ask about your database (example: 'count duplicates', 'avg age')")

# Step 1: Preview SQL
if st.button("1️⃣ Generate SQL"):
    if not q2.strip():
        st.warning("Enter a question.")
    else:
        resp, err = api_post("/debug_sql", data={"question": q2})
        if err:
            st.error(f"Backend Error: {err}")
        else:
            st.session_state["preview_sql"] = resp.get("sql")
            st.code(resp.get("sql"), language="sql")
            st.success("SQL generated successfully.")

# Step 2: Execute SQL
if "preview_sql" in st.session_state:
    if st.button("2️⃣ Execute SQL on CloudSQL"):
        resp, err = api_post("/nl_query_db", data={"question": q2, "target": "cloudsql"})
        if err:
            st.error(f"Backend Error: {err}")
        else:
            st.subheader("SQL Execution Result")
            st.code(resp.get("sql"), language="sql")
            st.json(resp.get("rows"))
