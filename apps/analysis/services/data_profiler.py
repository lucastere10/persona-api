"""
Enhanced Data Profiling Service

This service provides comprehensive data profiling using ydata_profiling,
health checks, and data quality assessments.
"""

import pandas as pd
import sqlite3
from ydata_profiling import ProfileReport
import json
import re
import numpy as np
import logging
from typing import Dict, List, Optional, Union, Any
try:
    from .file_reader import FileReader, read_data_file
except ImportError:
    from apps.analysis.services.file_reader import FileReader, read_data_file

logger = logging.getLogger(__name__)


class DataProfiler:
    """
    Enhanced data profiling service with health checks and quality assessments.
    """
    
    def __init__(self):
        self.file_reader = FileReader()
    
    def generate_profile_report(self, df: pd.DataFrame, title: str = "Data Profile Report") -> Dict[str, Any]:
        """
        Generate a comprehensive profile report using ydata_profiling.
        
        Args:
            df: DataFrame to profile
            title: Title for the report
            
        Returns:
            Dict: Profile report as dictionary
        """
        try:
            # Configure profile report
            profile_config = {
                "title": title,
                "explorative": True,
                "correlations": {
                    "auto": {"calculate": True},
                    "pearson": {"calculate": True},
                    "spearman": {"calculate": True},
                    "kendall": {"calculate": False},  # Can be slow for large datasets
                    "phi_k": {"calculate": True},
                    "cramers": {"calculate": True}
                },
                "missing_diagrams": {
                    "matrix": True,
                    "bar": True,
                    "heatmap": True,
                    "dendrogram": True
                },
                "interactions": {"targets": []},
                "vars": {
                    "num": {
                        "low_categorical_threshold": 5
                    }
                }
            }
            
            # Generate profile
            profile = ProfileReport(df, **profile_config)
            
            # Convert to JSON and parse back to dict
            json_str = profile.to_json()
            profile_dict = json.loads(json_str)
            
            logger.info(f"Generated profile report for dataset with shape {df.shape}")
            return profile_dict
            
        except Exception as e:
            logger.error(f"Error generating profile report: {e}")
            raise ValueError(f"Could not generate profile report: {e}")
    
    def perform_health_check(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform comprehensive health check on the dataset.
        
        Args:
            df: DataFrame to check
            
        Returns:
            Dict: Health check results
        """
        health_check = {
            "data_shape": df.shape,
            "data_types": df.dtypes.to_dict(),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
            "missing_data": {},
            "data_quality": {},
            "column_analysis": {},
            "recommendations": []
        }
        
        # Missing data analysis
        missing_counts = df.isnull().sum()
        missing_percentages = (missing_counts / len(df)) * 100
        
        health_check["missing_data"] = {
            "total_missing_values": missing_counts.sum(),
            "columns_with_missing": missing_counts[missing_counts > 0].to_dict(),
            "missing_percentages": missing_percentages[missing_percentages > 0].to_dict(),
            "completely_empty_columns": missing_percentages[missing_percentages == 100].index.tolist(),
            "heavily_missing_columns": missing_percentages[missing_percentages > 50].index.tolist()
        }
        
        # Data quality analysis
        health_check["data_quality"] = {
            "duplicate_rows": df.duplicated().sum(),
            "duplicate_percentage": (df.duplicated().sum() / len(df)) * 100,
            "unique_row_count": len(df.drop_duplicates()),
            "constant_columns": [],
            "high_cardinality_columns": [],
            "potential_id_columns": []
        }
        
        # Column-by-column analysis
        for col in df.columns:
            col_info = {
                "data_type": str(df[col].dtype),
                "unique_count": df[col].nunique(),
                "unique_percentage": (df[col].nunique() / len(df)) * 100,
                "missing_count": missing_counts[col],
                "missing_percentage": missing_percentages[col]
            }
            
            # Check for constant columns
            if df[col].nunique() <= 1:
                health_check["data_quality"]["constant_columns"].append(col)
            
            # Check for high cardinality
            if col_info["unique_percentage"] > 95 and df[col].nunique() > 100:
                health_check["data_quality"]["high_cardinality_columns"].append(col)
            
            # Check for potential ID columns
            if (col_info["unique_percentage"] == 100 and 
                any(keyword in col.lower() for keyword in ['id', 'key', 'index'])):
                health_check["data_quality"]["potential_id_columns"].append(col)
            
            # Numeric column analysis
            if pd.api.types.is_numeric_dtype(df[col]):
                col_info.update({
                    "min_value": df[col].min(),
                    "max_value": df[col].max(),
                    "mean": df[col].mean(),
                    "median": df[col].median(),
                    "std": df[col].std(),
                    "zeros_count": (df[col] == 0).sum(),
                    "zeros_percentage": ((df[col] == 0).sum() / len(df)) * 100,
                    "negative_count": (df[col] < 0).sum(),
                    "infinite_count": np.isinf(df[col]).sum()
                })
                
                # Outlier detection using IQR
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
                
                col_info.update({
                    "outliers_count": outliers,
                    "outliers_percentage": (outliers / len(df)) * 100,
                    "outlier_bounds": {"lower": lower_bound, "upper": upper_bound}
                })
            
            # Text column analysis
            elif pd.api.types.is_object_dtype(df[col]):
                non_null_series = df[col].dropna()
                if len(non_null_series) > 0:
                    col_info.update({
                        "avg_length": non_null_series.astype(str).str.len().mean(),
                        "max_length": non_null_series.astype(str).str.len().max(),
                        "min_length": non_null_series.astype(str).str.len().min(),
                        "empty_strings": (df[col] == "").sum(),
                        "whitespace_only": df[col].str.strip().eq("").sum() if pd.api.types.is_string_dtype(df[col]) else 0
                    })
            
            health_check["column_analysis"][col] = col_info
        
        # Generate recommendations
        health_check["recommendations"] = self._generate_recommendations(health_check)
        
        return health_check
    
    def _generate_recommendations(self, health_check: Dict) -> List[str]:
        """
        Generate data quality recommendations based on health check results.
        
        Args:
            health_check: Health check results
            
        Returns:
            List[str]: List of recommendations
        """
        recommendations = []
        
        # Missing data recommendations
        if health_check["missing_data"]["completely_empty_columns"]:
            recommendations.append(
                f"Consider removing completely empty columns: {', '.join(health_check['missing_data']['completely_empty_columns'])}"
            )
        
        if health_check["missing_data"]["heavily_missing_columns"]:
            recommendations.append(
                f"Columns with >50% missing data may need attention: {', '.join(health_check['missing_data']['heavily_missing_columns'])}"
            )
        
        # Duplicate data recommendations
        if health_check["data_quality"]["duplicate_percentage"] > 5:
            recommendations.append(
                f"High duplicate percentage ({health_check['data_quality']['duplicate_percentage']:.1f}%) - consider deduplication"
            )
        
        # Constant columns
        if health_check["data_quality"]["constant_columns"]:
            recommendations.append(
                f"Consider removing constant columns: {', '.join(health_check['data_quality']['constant_columns'])}"
            )
        
        # High cardinality columns
        if health_check["data_quality"]["high_cardinality_columns"]:
            recommendations.append(
                f"High cardinality columns may need special handling: {', '.join(health_check['data_quality']['high_cardinality_columns'])}"
            )
        
        # Memory usage recommendation
        if health_check["memory_usage_mb"] > 1000:
            recommendations.append(
                f"Large dataset ({health_check['memory_usage_mb']:.1f} MB) - consider data sampling or optimization"
            )
        
        # Column-specific recommendations
        for col, info in health_check["column_analysis"].items():
            if "outliers_percentage" in info and info["outliers_percentage"] > 10:
                recommendations.append(f"Column '{col}' has {info['outliers_percentage']:.1f}% outliers - consider investigation")
            
            if "zeros_percentage" in info and info["zeros_percentage"] > 50:
                recommendations.append(f"Column '{col}' has {info['zeros_percentage']:.1f}% zeros - verify data quality")
        
        return recommendations
    
    def profile_file(self, file_obj, filename: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Comprehensive file profiling including reading, health check, and ydata_profiling.
        
        Args:
            file_obj: File object to profile
            filename: Name of the file
            sheet_name: For Excel files, specific sheet to profile
            
        Returns:
            Dict: Complete profiling results
        """
        try:
            # Read the file
            data, file_info = read_data_file(file_obj, filename, sheet_name)
            
            result = {
                "file_info": file_info,
                "profiling_results": {}
            }
            
            # Handle multiple sheets (Excel files)
            if isinstance(data, dict):
                for sheet_name, df in data.items():
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        sheet_result = {
                            "health_check": self.perform_health_check(df),
                            "profile_report": self.generate_profile_report(df, f"Profile for {filename} - {sheet_name}")
                        }
                        result["profiling_results"][sheet_name] = sheet_result
                    else:
                        result["profiling_results"][sheet_name] = {"error": "Empty or invalid data"}
            
            # Handle single DataFrame
            elif isinstance(data, pd.DataFrame):
                if not data.empty:
                    result["profiling_results"]["main"] = {
                        "health_check": self.perform_health_check(data),
                        "profile_report": self.generate_profile_report(data, f"Profile for {filename}")
                    }
                else:
                    result["profiling_results"]["main"] = {"error": "Empty data"}
            
            else:
                raise ValueError("Unexpected data format returned from file reader")
            
            logger.info(f"Successfully profiled file: {filename}")
            return result
            
        except Exception as e:
            logger.error(f"Error profiling file {filename}: {e}")
            raise ValueError(f"Could not profile file: {e}")


# Legacy function for backward compatibility
def profile_file(file_obj, filename):
    """
    Legacy function - read file, run ydata_profiling, return JSON dict.
    """
    profiler = DataProfiler()
    result = profiler.profile_file(file_obj, filename)
    
    # Return only the profile report for backward compatibility
    if "main" in result["profiling_results"]:
        return result["profiling_results"]["main"].get("profile_report", {})
    elif len(result["profiling_results"]) == 1:
        sheet_name = list(result["profiling_results"].keys())[0]
        return result["profiling_results"][sheet_name].get("profile_report", {})
    else:
        return result
