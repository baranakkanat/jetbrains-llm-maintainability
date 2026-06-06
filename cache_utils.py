import pandas as pd
import os

CACHE_FILES = {
    "files": "cache_files.csv",
    "commits": "cache_commits.csv"
}

def cache_exists():
    return all(os.path.exists(f) for f in CACHE_FILES.values())

def save_cache(df_files, df_commits):
    df_files.to_csv(CACHE_FILES["files"], index=False)
    df_commits.to_csv(CACHE_FILES["commits"], index=False)
    print("Cache saved.")

def load_cache():
    df_files = pd.read_csv(CACHE_FILES["files"])
    df_commits = pd.read_csv(CACHE_FILES["commits"])
    df_files["date"] = pd.to_datetime(df_files["date"], utc=True)
    df_commits["date"] = pd.to_datetime(df_commits["date"], utc=True)
    print("Cache loaded.")
    return df_files, df_commits
