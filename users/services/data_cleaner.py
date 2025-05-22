import sqlite3
import pandas as pd
import numpy as np

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import IsolationForest

# --- custom transformer para remoção de outliers em todo o DataFrame ---
class _IsolationForestTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, contamination=0.05):
        self.contamination = contamination

    def fit(self, X, y=None):
        # X pode ser DataFrame ou ndarray; converte em DF para identificar numéricos
        X_df = X if isinstance(X, pd.DataFrame) else pd.DataFrame(X)
        self.num_cols_ = X_df.select_dtypes(include="number").columns.tolist()
        self.iforest_ = IsolationForest(contamination=self.contamination)
        # treina só nas colunas numéricas
        self.iforest_.fit(X_df[self.num_cols_])
        return self

    def transform(self, X):
        X_df = X if isinstance(X, pd.DataFrame) else pd.DataFrame(X, columns=self.num_cols_)
        mask = self.iforest_.predict(X_df[self.num_cols_]) == 1
        # mantém só as linhas não‑outliers
        return X_df.loc[mask].reset_index(drop=True)

# --- custom transformer para dropar colunas com muitos zeros ---
class _HighZeroDropper(BaseEstimator, TransformerMixin):
    def __init__(self, threshold=0.5):
        self.threshold = threshold

    def fit(self, X, y=None):
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)
        zero_frac = (X == 0).sum() / len(X)
        self.keep_cols_ = zero_frac[zero_frac <= self.threshold].index.tolist()
        return self

    def transform(self, X):
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)
        return X[self.keep_cols_]

    def get_feature_names_out(self, input_features=None):
        return np.array(self.keep_cols_)

# --- função que carrega o DataFrame (igual a sua) ---
def _load_df(file_obj, filename: str) -> pd.DataFrame:
    name = filename.lower()
    if name.endswith('.csv'):
        try:
            return pd.read_csv(file_obj)
        except pd.errors.ParserError:
            file_obj.seek(0)
            return pd.read_csv(file_obj, sep='\t')
    elif name.endswith(('.xls', '.xlsx')):
        return pd.read_excel(file_obj)
    elif name.endswith('.sql'):
        sql_text = file_obj.read().decode('utf-8')
        conn = sqlite3.connect(':memory:')
        conn.executescript(sql_text)
        tbl = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchone()[0]
        df = pd.read_sql_query(f"SELECT * FROM {tbl}", conn)
        conn.close()
        return df
    else:
        raise ValueError(f"Unsupported file type: {filename}")

# --- pipeline reorganizada ---
def build_cleaning_pipeline(df: pd.DataFrame,
                            zero_threshold: float = 0.5,
                            outlier_contamination: float = 0.05):
    # 1) identifica colunas numéricas e categóricas
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    # 2) pipeline **SEM** remoção de outliers (será feita antes)
    num_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("zero_drop", _HighZeroDropper(threshold=zero_threshold)),
        ("scaler", StandardScaler()),
    ])

    # 3) pipeline de categóricas
    cat_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="__missing__")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    # 4) preprocessor que só aplica transformações por coluna
    preprocessor = ColumnTransformer([
        ("nums", num_pipeline, num_cols),
        ("cats", cat_pipeline, cat_cols),
    ], remainder="drop")

    # 5) pipeline final: outlier → column‑wise transforms
    return Pipeline([
        ("outlier_removal", _IsolationForestTransformer(contamination=outlier_contamination)),
        ("preprocessor", preprocessor),
    ])

# --- clean_file usando a nova pipeline ---
def clean_file(file_obj, filename,
               zero_threshold: float = 0.5,
               outlier_contamination: float = 0.05) -> dict:
    df = _load_df(file_obj, filename)

    pipeline = build_cleaning_pipeline(df, zero_threshold, outlier_contamination)
    # fit_transform retorna DataFrame limpo (após remoção de linhas e colunas)
    df_clean = pipeline.fit_transform(df)

    # Se você quiser garantir DataFrame em vez de ndarray:
    if isinstance(df_clean, np.ndarray):
        # retorna as colunas geradas pelo preprocessor
        cols = pipeline.named_steps["preprocessor"].get_feature_names_out()
        df_clean = pd.DataFrame(df_clean, columns=cols)

    return {
        "cleaned_row_count": len(df_clean),
        "cleaned_columns": list(df_clean.columns),
        "cleaned_preview": df_clean.head(10).to_dict(orient="records")
    }
