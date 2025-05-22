import pandas as pd
import sqlite3
from ydata_profiling import ProfileReport
import json
import re
import numpy as np

def profile_file(file_obj, filename):
    """
    Read `file_obj` (CSV, Excel, or SQL dump), run ydata_profiling,
    and return a JSON-serializable dict.
    """
    # 1️⃣ Load into DataFrame
    if filename.endswith('.csv'):
        df = pd.read_csv(file_obj)
    elif filename.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file_obj)
    elif filename.endswith('.sql'):
        sql_text = file_obj.read().decode('utf-8')
        conn = sqlite3.connect(':memory:')
        conn.executescript(sql_text)
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchone()[0]
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        conn.close()
    else:
        raise ValueError(f"Unsupported file type: {filename}")

    # 2️⃣ Generate profile and serialize to dict
    profile = ProfileReport(df, title="Data Profile Report", explorative=True, sample=None)
    json_str = profile.to_json()           # get a JSON string
    profile_dict = json.loads(json_str)    # parse back into a dict
    return profile_dict
