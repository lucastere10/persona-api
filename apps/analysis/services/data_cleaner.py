"""
Enhanced Data Cleaning Service

This service provides intelligent data cleaning based on health check results,
including handling of null values, outliers, and data quality issues.
"""

import sqlite3
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any, Union

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.ensemble import IsolationForest

try:
    from .data_profiler import DataProfiler
    from .file_reader import read_data_file
except ImportError:
    from apps.analysis.services.data_profiler import DataProfiler
    from apps.analysis.services.file_reader import read_data_file

logger = logging.getLogger(__name__)


class DataCleaner:
    """
    Intelligent data cleaning service that uses health check results to guide cleaning operations.
    """
    
    def __init__(self):
        self.profiler = DataProfiler()
        self.cleaning_log = []
    
    def clean_dataset(self, df: pd.DataFrame, health_check: Optional[Dict] = None, 
                     cleaning_config: Optional[Dict] = None) -> Tuple[pd.DataFrame, Dict]:
        """
        Perform comprehensive data cleaning based on health check results.
        
        Args:
            df: DataFrame to clean
            health_check: Pre-computed health check results (optional)
            cleaning_config: Configuration for cleaning operations
            
        Returns:
            Tuple[cleaned_df, cleaning_report]: Cleaned data and cleaning report
        """
        # Perform health check if not provided
        if health_check is None:
            health_check = self.profiler.perform_health_check(df)
        
        # Default cleaning configuration
        default_config = {
            "remove_empty_columns": True,
            "remove_constant_columns": True,
            "handle_duplicates": True,
            "null_threshold": 0.5,  # Remove columns with >50% nulls
            "outlier_method": "iqr",  # "iqr", "isolation_forest", or "none"
            "outlier_threshold": 0.05,  # Remove if >5% outliers
            "imputation_strategy": "intelligent",  # "intelligent", "drop", "mean", "median", "mode"
            "encoding_strategy": "auto"  # "auto", "onehot", "label", "none"
        }
        
        if cleaning_config:
            default_config.update(cleaning_config)
        
        config = default_config
        
        # Initialize cleaning report
        cleaning_report = {
            "original_shape": df.shape,
            "operations_performed": [],
            "columns_removed": [],
            "columns_modified": [],
            "rows_removed": 0,
            "cleaning_summary": {}
        }
        
        self.cleaning_log = []
        df_clean = df.copy()
        
        # 1. Remove completely empty columns
        if config["remove_empty_columns"]:
            empty_cols = health_check["missing_data"]["completely_empty_columns"]
            if empty_cols:
                df_clean = df_clean.drop(columns=empty_cols)
                cleaning_report["columns_removed"].extend(empty_cols)
                self._log_operation(f"Removed {len(empty_cols)} completely empty columns")
        
        # 2. Remove constant columns
        if config["remove_constant_columns"]:
            constant_cols = health_check["data_quality"]["constant_columns"]
            if constant_cols:
                df_clean = df_clean.drop(columns=constant_cols)
                cleaning_report["columns_removed"].extend(constant_cols)
                self._log_operation(f"Removed {len(constant_cols)} constant columns")
        
        # 3. Handle heavily missing columns
        if config["null_threshold"] < 1.0:
            heavily_missing = []
            for col, percentage in health_check["missing_data"]["missing_percentages"].items():
                if col in df_clean.columns and percentage > config["null_threshold"] * 100:
                    heavily_missing.append(col)
            
            if heavily_missing:
                df_clean = df_clean.drop(columns=heavily_missing)
                cleaning_report["columns_removed"].extend(heavily_missing)
                self._log_operation(f"Removed {len(heavily_missing)} columns with >{config['null_threshold']*100}% missing values")
        
        # 4. Handle duplicates
        if config["handle_duplicates"]:
            initial_rows = len(df_clean)
            df_clean = df_clean.drop_duplicates()
            rows_removed = initial_rows - len(df_clean)
            if rows_removed > 0:
                cleaning_report["rows_removed"] += rows_removed
                self._log_operation(f"Removed {rows_removed} duplicate rows")
        
        # 5. Handle outliers
        if config["outlier_method"] != "none":
            df_clean, outlier_report = self._handle_outliers(df_clean, health_check, config)
            if outlier_report["rows_removed"] > 0:
                cleaning_report["rows_removed"] += outlier_report["rows_removed"]
                cleaning_report["columns_modified"].extend(outlier_report["columns_processed"])
                self._log_operation(f"Handled outliers: {outlier_report['summary']}")
        
        # 6. Handle missing values
        if config["imputation_strategy"] != "none":
            df_clean, imputation_report = self._handle_missing_values(df_clean, health_check, config)
            cleaning_report["columns_modified"].extend(imputation_report["columns_imputed"])
            self._log_operation(f"Imputed missing values: {imputation_report['summary']}")
        
        # 7. Handle encoding (if requested)
        if config["encoding_strategy"] != "none":
            df_clean, encoding_report = self._handle_encoding(df_clean, config)
            cleaning_report["columns_modified"].extend(encoding_report["columns_encoded"])
            if encoding_report["columns_encoded"]:
                self._log_operation(f"Encoded categorical variables: {encoding_report['summary']}")
        
        # Final report
        cleaning_report["final_shape"] = df_clean.shape
        cleaning_report["operations_performed"] = self.cleaning_log
        cleaning_report["cleaning_summary"] = {
            "columns_removed_count": len(set(cleaning_report["columns_removed"])),
            "columns_modified_count": len(set(cleaning_report["columns_modified"])),
            "rows_removed_count": cleaning_report["rows_removed"],
            "data_reduction_percentage": (1 - (df_clean.size / df.size)) * 100
        }
        
        logger.info(f"Data cleaning completed. Shape: {df.shape} -> {df_clean.shape}")
        return df_clean, cleaning_report
    
    def _handle_outliers(self, df: pd.DataFrame, health_check: Dict, config: Dict) -> Tuple[pd.DataFrame, Dict]:
        """Handle outliers based on the specified method."""
        outlier_report = {
            "rows_removed": 0,
            "columns_processed": [],
            "summary": ""
        }
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if config["outlier_method"] == "iqr":
            # Use IQR method for each numeric column
            mask = pd.Series([True] * len(df), index=df.index)
            
            for col in numeric_cols:
                col_info = health_check["column_analysis"].get(col, {})
                outlier_percentage = col_info.get("outliers_percentage", 0)
                
                if outlier_percentage > config["outlier_threshold"] * 100:
                    bounds = col_info.get("outlier_bounds", {})
                    if bounds:
                        lower, upper = bounds["lower"], bounds["upper"]
                        col_mask = (df[col] >= lower) & (df[col] <= upper)
                        mask = mask & col_mask
                        outlier_report["columns_processed"].append(col)
            
            initial_rows = len(df)
            df_clean = df[mask].copy()
            outlier_report["rows_removed"] = initial_rows - len(df_clean)
            outlier_report["summary"] = f"IQR method on {len(outlier_report['columns_processed'])} columns"
            
        elif config["outlier_method"] == "isolation_forest":
            # Use Isolation Forest for multivariate outlier detection
            if len(numeric_cols) > 0:
                isolation_forest = IsolationForest(contamination=config["outlier_threshold"], random_state=42)
                outlier_predictions = isolation_forest.fit_predict(df[numeric_cols].fillna(df[numeric_cols].median()))
                
                initial_rows = len(df)
                df_clean = df[outlier_predictions == 1].copy()
                outlier_report["rows_removed"] = initial_rows - len(df_clean)
                outlier_report["columns_processed"] = numeric_cols
                outlier_report["summary"] = f"Isolation Forest on {len(numeric_cols)} numeric columns"
            else:
                df_clean = df.copy()
                outlier_report["summary"] = "No numeric columns for outlier detection"
        
        return df_clean, outlier_report
    
    def _handle_missing_values(self, df: pd.DataFrame, health_check: Dict, config: Dict) -> Tuple[pd.DataFrame, Dict]:
        """Handle missing values using intelligent imputation strategies."""
        imputation_report = {
            "columns_imputed": [],
            "summary": {}
        }
        
        df_clean = df.copy()
        
        for col in df.columns:
            missing_percentage = health_check["missing_data"]["missing_percentages"].get(col, 0)
            
            if missing_percentage > 0:
                col_info = health_check["column_analysis"][col]
                
                if config["imputation_strategy"] == "intelligent":
                    # Choose strategy based on data type and missing percentage
                    if missing_percentage > 30:
                        # High missing percentage - consider dropping or forward fill
                        if pd.api.types.is_numeric_dtype(df_clean[col]):
                            df_clean[col].fillna(df_clean[col].median(), inplace=True)
                            strategy = "median"
                        else:
                            df_clean[col].fillna(df_clean[col].mode().iloc[0] if not df_clean[col].mode().empty else "Unknown", inplace=True)
                            strategy = "mode"
                    else:
                        # Lower missing percentage - use more sophisticated methods
                        if pd.api.types.is_numeric_dtype(df_clean[col]):
                            if col_info.get("unique_percentage", 0) < 10:  # Low cardinality numeric
                                df_clean[col].fillna(df_clean[col].mode().iloc[0] if not df_clean[col].mode().empty else df_clean[col].median(), inplace=True)
                                strategy = "mode"
                            else:
                                df_clean[col].fillna(df_clean[col].mean(), inplace=True)
                                strategy = "mean"
                        else:
                            df_clean[col].fillna(df_clean[col].mode().iloc[0] if not df_clean[col].mode().empty else "Unknown", inplace=True)
                            strategy = "mode"
                
                elif config["imputation_strategy"] == "drop":
                    df_clean = df_clean.dropna(subset=[col])
                    strategy = "drop_rows"
                
                elif config["imputation_strategy"] in ["mean", "median", "mode"]:
                    if pd.api.types.is_numeric_dtype(df_clean[col]):
                        if config["imputation_strategy"] == "mean":
                            df_clean[col].fillna(df_clean[col].mean(), inplace=True)
                        else:
                            df_clean[col].fillna(df_clean[col].median(), inplace=True)
                    else:
                        df_clean[col].fillna(df_clean[col].mode().iloc[0] if not df_clean[col].mode().empty else "Unknown", inplace=True)
                    strategy = config["imputation_strategy"]
                
                imputation_report["columns_imputed"].append(col)
                imputation_report["summary"][col] = f"{strategy} (was {missing_percentage:.1f}% missing)"
        
        return df_clean, imputation_report
    
    def _handle_encoding(self, df: pd.DataFrame, config: Dict) -> Tuple[pd.DataFrame, Dict]:
        """Handle encoding of categorical variables."""
        encoding_report = {
            "columns_encoded": [],
            "summary": {}
        }
        
        df_clean = df.copy()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        for col in categorical_cols:
            unique_count = df_clean[col].nunique()
            
            if config["encoding_strategy"] == "auto":
                # Choose encoding strategy based on cardinality
                if unique_count <= 10:  # Low cardinality - use one-hot encoding
                    dummies = pd.get_dummies(df_clean[col], prefix=col, drop_first=True)
                    df_clean = pd.concat([df_clean.drop(columns=[col]), dummies], axis=1)
                    encoding_report["columns_encoded"].append(col)
                    encoding_report["summary"][col] = f"one-hot ({unique_count} categories)"
                elif unique_count <= 50:  # Medium cardinality - use label encoding
                    le = LabelEncoder()
                    df_clean[col] = le.fit_transform(df_clean[col].astype(str))
                    encoding_report["columns_encoded"].append(col)
                    encoding_report["summary"][col] = f"label ({unique_count} categories)"
                # High cardinality - leave as is
            
            elif config["encoding_strategy"] == "onehot" and unique_count <= 20:
                dummies = pd.get_dummies(df_clean[col], prefix=col, drop_first=True)
                df_clean = pd.concat([df_clean.drop(columns=[col]), dummies], axis=1)
                encoding_report["columns_encoded"].append(col)
                encoding_report["summary"][col] = f"one-hot ({unique_count} categories)"
            
            elif config["encoding_strategy"] == "label":
                le = LabelEncoder()
                df_clean[col] = le.fit_transform(df_clean[col].astype(str))
                encoding_report["columns_encoded"].append(col)
                encoding_report["summary"][col] = f"label ({unique_count} categories)"
        
        return df_clean, encoding_report
    
    def _log_operation(self, message: str):
        """Log a cleaning operation."""
        self.cleaning_log.append(message)
        logger.info(f"Data cleaning: {message}")
    
    def clean_file(self, file_obj, filename: str, sheet_name: Optional[str] = None,
                   cleaning_config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Clean a data file with comprehensive profiling and cleaning.
        
        Args:
            file_obj: File object to clean
            filename: Name of the file
            sheet_name: For Excel files, specific sheet to clean
            cleaning_config: Configuration for cleaning operations
            
        Returns:
            Dict: Cleaning results including cleaned data and reports
        """
        try:
            # Read and profile the file
            profiling_result = self.profiler.profile_file(file_obj, filename, sheet_name)
            
            # Read the raw data again for cleaning
            data, file_info = read_data_file(file_obj, filename, sheet_name)
            
            result = {
                "file_info": file_info,
                "original_profiling": profiling_result["profiling_results"],
                "cleaning_results": {}
            }
            
            # Handle multiple sheets (Excel files)
            if isinstance(data, dict):
                for sheet_name, df in data.items():
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        health_check = profiling_result["profiling_results"][sheet_name]["health_check"]
                        cleaned_df, cleaning_report = self.clean_dataset(df, health_check, cleaning_config)
                        
                        # Generate new health check for cleaned data
                        cleaned_health_check = self.profiler.perform_health_check(cleaned_df)
                        
                        result["cleaning_results"][sheet_name] = {
                            "cleaned_data": cleaned_df,
                            "cleaning_report": cleaning_report,
                            "cleaned_health_check": cleaned_health_check
                        }
                    else:
                        result["cleaning_results"][sheet_name] = {"error": "Empty or invalid data"}
            
            # Handle single DataFrame
            elif isinstance(data, pd.DataFrame):
                if not data.empty:
                    health_check = profiling_result["profiling_results"]["main"]["health_check"]
                    cleaned_df, cleaning_report = self.clean_dataset(data, health_check, cleaning_config)
                    
                    # Generate new health check for cleaned data
                    cleaned_health_check = self.profiler.perform_health_check(cleaned_df)
                    
                    result["cleaning_results"]["main"] = {
                        "cleaned_data": cleaned_df,
                        "cleaning_report": cleaning_report,
                        "cleaned_health_check": cleaned_health_check
                    }
                else:
                    result["cleaning_results"]["main"] = {"error": "Empty data"}
            
            logger.info(f"Successfully cleaned file: {filename}")
            return result
            
        except Exception as e:
            logger.error(f"Error cleaning file {filename}: {e}")
            raise ValueError(f"Could not clean file: {e}")


# --- Legacy transformer classes for backward compatibility ---
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
