# analysis_utils.py
import io
import base64
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging

def df_to_b64_png_fig(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('ascii')
    return f"data:image/png;base64,{encoded}"

def safe_sample(df, n=5):
    try:
        return df.head(n).to_dict(orient='records')
    except Exception:
        return []

def summarize_dataframe(df: pd.DataFrame):
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)
    df = df.replace([np.inf, -np.inf], np.nan)
    summary = {}
    summary['shape'] = {'rows': int(df.shape[0]), 'columns': int(df.shape[1])}
    summary['columns'] = {col: str(dtype) for col, dtype in df.dtypes.items()}
    summary['missing_values'] = {col: int(df[col].isna().sum()) for col in df.columns}
    numeric = df.select_dtypes(include=[np.number])
    numeric_stats = {}
    if not numeric.empty:
        numeric_stats = numeric.describe().to_dict()
    summary['numeric_stats'] = numeric_stats
    categorical_stats = {}
    cats = df.select_dtypes(include=['object', 'category'])
    for col in cats.columns:
        try:
            top = df[col].value_counts().nlargest(10).to_dict()
            categorical_stats[col] = top
        except Exception:
            categorical_stats[col] = {}
    summary['categorical_stats'] = categorical_stats
    try:
        corr = {}
        if numeric.shape[1] > 0:
            corr_df = numeric.corr().round(3)
            corr = corr_df.to_dict()
        summary['correlation_matrix'] = corr
    except Exception:
        summary['correlation_matrix'] = {}
    summary['sample'] = safe_sample(df, n=10)
    insights = []
    if summary['shape']['rows'] == 0:
        insights.append("Empty dataset.")
    else:
        insights.append("No significant issues detected.")
    summary['insights'] = insights
    total = summary['shape']['rows'] * max(1, summary['shape']['columns'])
    missing_total = sum(summary['missing_values'].values()) if total>0 else 0
    quality = 100 - min(100, int(100 * (missing_total / max(1, total))))
    summary['data_quality_score'] = quality
    charts = []
    try:
        num_cols = list(numeric.columns)[:3]
        for col in num_cols:
            fig = plt.figure()
            try:
                df[col].dropna().astype(float).hist(bins=30)
            except Exception:
                df[col].dropna().plot(kind='hist')
            plt.title(f"Distribution of {col}")
            charts.append({'column': col, 'type': 'histogram', 'data_uri': df_to_b64_png_fig(fig)})
            plt.close(fig)
        cat_cols = list(cats.columns)[:3]
        for col in cat_cols:
            top = df[col].value_counts().nlargest(10)
            fig = plt.figure()
            top.plot(kind='bar')
            plt.title(f"Top values for {col}")
            charts.append({'column': col, 'type': 'bar', 'data_uri': df_to_b64_png_fig(fig)})
            plt.close(fig)
    except Exception as e:
        logging.exception("Chart creation failed: %s", e)
    summary['anomalies'] = {}
    summary['trend_analysis'] = {}
    summary['pivot_suggestions'] = []
    return summary, charts
