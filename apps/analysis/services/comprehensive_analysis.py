"""
Comprehensive Analysis Integration Example

This script demonstrates the complete workflow using all analysis services
together with OpenAI integration for intelligent insights.
"""

import pandas as pd
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Import the analysis services (use absolute imports for Django projects)
from apps.analysis.services.file_reader import FileReader, read_data_file, get_excel_info
from apps.analysis.services.data_profiler import DataProfiler
from apps.analysis.services.data_cleaner import DataCleaner
from apps.analysis.services.openai_api_request import OpenAIService


class ComprehensiveAnalysisService:
    """
    Complete analysis service that combines all individual services
    for a comprehensive data analysis workflow.
    """
    
    def __init__(self, use_openai: bool = True):
        """
        Initialize the comprehensive analysis service.
        
        Args:
            use_openai: Whether to use OpenAI for intelligent insights
        """
        self.file_reader = FileReader()
        self.profiler = DataProfiler()
        self.cleaner = DataCleaner()
        self.use_openai = use_openai
        
        if use_openai:
            try:
                self.openai_service = OpenAIService()
                # Test connection
                test_result = self.openai_service.test_connection()
                if not test_result['success']:
                    logger.warning("OpenAI connection failed. AI insights will be disabled.")
                    self.use_openai = False
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI service: {e}")
                self.use_openai = False
    
    def analyze_file(self, file_path: str, sheet_name: Optional[str] = None, 
                    cleaning_config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Perform complete analysis of a data file.
        
        Args:
            file_path: Path to the data file
            sheet_name: For Excel files, specific sheet to analyze
            cleaning_config: Configuration for data cleaning
            
        Returns:
            Dict: Complete analysis results
        """
        logger.info(f"Starting comprehensive analysis of: {file_path}")
        
        analysis_results = self._initialize_analysis_results(file_path)
        
        # Step 1: File Reading and Initial Assessment
        datasets = self._read_and_validate_file(file_path, sheet_name, analysis_results)
        if not datasets:
            return self._make_serializable(analysis_results)
        
        # Step 2: Data Profiling and Health Check
        self._perform_data_profiling(datasets, analysis_results)
        
        # Step 3: Data Cleaning
        self._perform_data_cleaning(datasets, cleaning_config, analysis_results)
        
        # Step 4: AI-Powered Insights (if enabled)
        if self.use_openai:
            self._generate_ai_insights(analysis_results)
        
        # Step 5: Generate Summary and Recommendations
        self._generate_final_summary(analysis_results)
        
        logger.info("Comprehensive analysis completed successfully!")
        return self._make_serializable(analysis_results)

    def _initialize_analysis_results(self, file_path: str) -> Dict[str, Any]:
        """Initialize the analysis results structure."""
        return {
            "file_path": file_path,
            "timestamp": pd.Timestamp.now().isoformat(),
            "steps_completed": [],
            "errors": [],
            "results": {}
        }

    def _read_and_validate_file(self, file_path: str, sheet_name: Optional[str], 
                               analysis_results: Dict[str, Any]) -> Optional[Dict]:
        """Read and validate the input file."""
        logger.info("Step 1: Reading and validating file...")
        
        try:
            with open(file_path, 'rb') as file_obj:
                filename = self._get_filename(file_path, file_obj)
                
                # Get file information
                file_info = self.file_reader.get_file_info(file_obj, filename)
                analysis_results["results"]["file_info"] = file_info
                
                # Handle Excel worksheets
                self._handle_excel_worksheets(file_info, sheet_name)
                
                # Read the data
                data, _ = read_data_file(file_obj, filename, sheet_name)
                analysis_results["results"]["data_loaded"] = True
                analysis_results["steps_completed"].append("file_reading")
                
                # Determine data structure
                datasets = {"main": data} if isinstance(data, pd.DataFrame) else data
                logger.info(f"Successfully loaded {len(datasets)} dataset(s)")
                
                return datasets
                
        except Exception as e:
            error_msg = f"File reading failed: {str(e)}"
            logger.error(error_msg)
            analysis_results["errors"].append(error_msg)
            return None

    def _get_filename(self, file_path: str, file_obj) -> str:
        """Get the filename, handling temporary files from DRF."""
        filename = Path(file_path).name
        
        # Handle files without extension (temp files)
        if not filename or '.' not in filename:
            original_filename = getattr(file_obj, 'original_filename', None)
            if original_filename:
                filename = original_filename
                
        return filename

    def _handle_excel_worksheets(self, file_info: Dict, sheet_name: Optional[str]):
        """Handle Excel files with multiple worksheets."""
        if file_info['file_type'] == 'excel' and not sheet_name:
            worksheets = file_info.get('worksheets', [])
            if len(worksheets) > 1:
                logger.info(f"Multiple worksheets found: {worksheets}")
                logger.info("Analyzing all worksheets...")

    def _perform_data_profiling(self, datasets: Dict, analysis_results: Dict[str, Any]):
        """Perform data profiling and health checks on all datasets."""
        logger.info("Step 2: Performing data profiling and health checks...")
        analysis_results["results"]["datasets"] = {}
        
        for dataset_name, df in datasets.items():
            self._profile_single_dataset(dataset_name, df, analysis_results)
        
        analysis_results["steps_completed"].append("data_profiling")

    def _profile_single_dataset(self, dataset_name: str, df: pd.DataFrame, 
                               analysis_results: Dict[str, Any]):
        """Profile a single dataset."""
        logger.info(f"Analyzing dataset: {dataset_name}")
        dataset_results = {}
        
        try:
            # Health check
            health_check = self.profiler.perform_health_check(df)
            dataset_results["health_check"] = health_check
            
            # Generate profile report (limited for large datasets)
            if df.size < 1000000:  # Less than 1M cells
                profile_report = self.profiler.generate_profile_report(df, f"Profile for {dataset_name}")
                dataset_results["profile_report"] = profile_report
            else:
                logger.info(f"Dataset {dataset_name} is large ({df.shape}). Skipping detailed profiling.")
                dataset_results["profile_report"] = {"note": "Skipped for large dataset"}
            
            # Log key findings
            self._log_health_check_summary(dataset_name, health_check)
            analysis_results["results"]["datasets"][dataset_name] = dataset_results
            
        except Exception as e:
            error_msg = f"Profiling failed for {dataset_name}: {str(e)}"
            logger.error(error_msg)
            analysis_results["errors"].append(error_msg)

    def _perform_data_cleaning(self, datasets: Dict, cleaning_config: Optional[Dict], 
                             analysis_results: Dict[str, Any]):
        """Perform data cleaning on all datasets."""
        logger.info("Step 3: Performing intelligent data cleaning...")
        
        for dataset_name, df in datasets.items():
            if dataset_name in analysis_results["results"]["datasets"]:
                self._clean_single_dataset(dataset_name, df, cleaning_config, analysis_results)
        
        analysis_results["steps_completed"].append("data_cleaning")

    def _clean_single_dataset(self, dataset_name: str, df: pd.DataFrame, 
                            cleaning_config: Optional[Dict], analysis_results: Dict[str, Any]):
        """Clean a single dataset."""
        try:
            health_check = analysis_results["results"]["datasets"][dataset_name]["health_check"]
            
            # Use provided config or create intelligent default
            config = cleaning_config or self._generate_intelligent_cleaning_config(health_check)
            
            logger.info(f"Cleaning {dataset_name} with config: {config}")
            cleaned_df, cleaning_report = self.cleaner.clean_dataset(df, health_check, config)
            
            # Post-cleaning health check
            cleaned_health_check = self.profiler.perform_health_check(cleaned_df)
            
            # Store cleaning results
            analysis_results["results"]["datasets"][dataset_name].update({
                "original_data_shape": df.shape,
                "cleaned_data_shape": cleaned_df.shape,
                "cleaning_report": cleaning_report,
                "cleaned_health_check": cleaned_health_check,
                "cleaning_config_used": config
            })
            
            # Log cleaning summary
            self._log_cleaning_summary(dataset_name, cleaning_report)
            
        except Exception as e:
            error_msg = f"Cleaning failed for {dataset_name}: {str(e)}"
            logger.error(error_msg)
            analysis_results["errors"].append(error_msg)

    def _generate_ai_insights(self, analysis_results: Dict[str, Any]):
        """Generate AI-powered insights for all datasets."""
        logger.info("Step 4: Generating AI-powered insights...")
        
        for dataset_name in analysis_results["results"]["datasets"]:
            self._generate_ai_insights_for_dataset(dataset_name, analysis_results)
        
        analysis_results["steps_completed"].append("ai_insights")

    def _generate_ai_insights_for_dataset(self, dataset_name: str, analysis_results: Dict[str, Any]):
        """Generate AI insights for a single dataset."""
        try:
            dataset_results = analysis_results["results"]["datasets"][dataset_name]
            
            # Generate overall insights if we have the required data
            if "health_check" in dataset_results and "cleaning_report" in dataset_results:
                ai_insights = self.openai_service.generate_data_analysis_insights(
                    dataset_results["health_check"],
                    dataset_results["cleaning_report"]
                )
                
                if ai_insights["success"]:
                    dataset_results["ai_insights"] = ai_insights
                    logger.info(f"Generated AI insights for {dataset_name}")
                else:
                    logger.warning(f"AI insights generation failed for {dataset_name}")
            
            # Generate analysis approach suggestions
            dataset_summary = self._create_dataset_summary(dataset_results)
            approach_suggestions = self.openai_service.suggest_analysis_approach(dataset_summary)
            
            if approach_suggestions["success"]:
                dataset_results["analysis_suggestions"] = approach_suggestions
                logger.info(f"Generated analysis approach suggestions for {dataset_name}")
        
        except Exception as e:
            error_msg = f"AI insights generation failed for {dataset_name}: {str(e)}"
            logger.error(error_msg)
            analysis_results["errors"].append(error_msg)

    def _generate_final_summary(self, analysis_results: Dict[str, Any]):
        """Generate final summary and recommendations."""
        logger.info("Step 5: Generating final summary and recommendations...")
        analysis_results["results"]["summary"] = self._generate_analysis_summary(analysis_results)
        analysis_results["steps_completed"].append("summary_generation")
        analysis_results["processing_completed"] = pd.Timestamp.now().isoformat()
    
    def _generate_intelligent_cleaning_config(self, health_check: Dict) -> Dict:
        """Generate intelligent cleaning configuration based on health check results."""
        config = {
            "remove_empty_columns": True,
            "remove_constant_columns": True,
            "handle_duplicates": True,
            "null_threshold": 0.7,  # Default
            "outlier_method": "iqr",
            "outlier_threshold": 0.05,
            "imputation_strategy": "intelligent",
            "encoding_strategy": "auto"
        }
        
        # Adjust based on data characteristics
        missing_data = health_check.get("missing_data", {})
        data_quality = health_check.get("data_quality", {})
        
        # More aggressive cleaning for heavily corrupted data
        if missing_data.get("total_missing_values", 0) > health_check["data_shape"][0] * health_check["data_shape"][1] * 0.3:
            config["null_threshold"] = 0.5  # More aggressive
            logger.info("High missing data detected - using more aggressive cleaning")
        
        # Handle high duplicate percentage
        if data_quality.get("duplicate_percentage", 0) > 20:
            logger.info("High duplicate percentage detected - prioritizing deduplication")
        
        # Adjust outlier handling for small datasets
        if health_check["data_shape"][0] < 1000:
            config["outlier_method"] = "none"  # Don't remove outliers for small datasets
            logger.info("Small dataset detected - disabling outlier removal")
        
        return config
    
    def _log_health_check_summary(self, dataset_name: str, health_check: Dict):
        """Log a summary of health check results."""
        logger.info(f"Health Check Summary for {dataset_name}:")
        logger.info(f"  - Shape: {health_check['data_shape']}")
        logger.info(f"  - Missing values: {health_check['missing_data']['total_missing_values']}")
        logger.info(f"  - Duplicate rows: {health_check['data_quality']['duplicate_rows']}")
        logger.info(f"  - Memory usage: {health_check['memory_usage_mb']:.1f} MB")
        
        if health_check.get('recommendations'):
            logger.info(f"  - Key recommendations: {len(health_check['recommendations'])}")
    
    def _log_cleaning_summary(self, dataset_name: str, cleaning_report: Dict):
        """Log a summary of cleaning results."""
        summary = cleaning_report.get('cleaning_summary', {})
        logger.info(f"Cleaning Summary for {dataset_name}:")
        logger.info(f"  - Original shape: {cleaning_report['original_shape']}")
        logger.info(f"  - Final shape: {cleaning_report['final_shape']}")
        logger.info(f"  - Columns removed: {summary.get('columns_removed_count', 0)}")
        logger.info(f"  - Rows removed: {summary.get('rows_removed_count', 0)}")
        logger.info(f"  - Data reduction: {summary.get('data_reduction_percentage', 0):.1f}%")
    
    def _create_dataset_summary(self, dataset_results: Dict) -> Dict:
        """Create a JSON-safe summary for AI analysis."""
        hc = dataset_results.get("health_check", {})
        shape = hc.get("data_shape", [0, 0])
        rows, cols = int(shape[0]), int(shape[1])

        # Data types como str para evitar Int64Dtype, etc.
        raw_dtypes = hc.get("data_types", {})
        data_types = {col: str(dtype) for col, dtype in raw_dtypes.items()}

        # Total de células = linhas * colunas (protege divisão por zero)
        total_cells = rows * cols or 1
        missing_vals = hc.get("missing_data", {}).get("total_missing_values", 0)
        missing_percentage = float(missing_vals) / total_cells * 100

        # Duplicatas
        dup_rows = hc.get("data_quality", {}).get("duplicate_rows", 0)
        has_duplicates = bool(dup_rows > 0)

        memory_mb = hc.get("memory_usage_mb", 0.0)
        memory_usage_mb = float(memory_mb)

        return {
            "shape": [rows, cols],
            "row_count": rows,
            "column_count": cols,
            "data_types": data_types,
            "missing_percentage": missing_percentage,
            "has_duplicates": has_duplicates,
            "memory_usage_mb": memory_usage_mb
        }

    def _generate_analysis_summary(self, analysis_results: Dict) -> Dict:
        """Generate final analysis summary."""
        datasets = analysis_results.get("results", {}).get("datasets", {})
        
        summary = {
            "total_datasets_analyzed": len(datasets),
            "steps_completed": analysis_results.get("steps_completed", []),
            "errors_encountered": len(analysis_results.get("errors", [])),
            "ai_insights_generated": self.use_openai,
            "overall_success": len(analysis_results.get("errors", [])) == 0,
            "datasets_summary": {}
        }
        
        for dataset_name, dataset_results in datasets.items():
            dataset_summary = {
                "original_shape": dataset_results.get("original_data_shape"),
                "cleaned_shape": dataset_results.get("cleaned_data_shape"),
                "health_score": self._calculate_health_score(dataset_results.get("health_check", {})),
                "cleaning_effectiveness": self._calculate_cleaning_effectiveness(dataset_results.get("cleaning_report", {}))
            }
            summary["datasets_summary"][dataset_name] = dataset_summary
        
        return summary
    
    def _calculate_health_score(self, health_check: Dict) -> float:
        """Calculate a simple health score (0-10) based on health check results."""
        if not health_check:
            return 0.0
        
        score = 10.0
        
        # Deduct for missing data
        missing_data = health_check.get("missing_data", {})
        total_cells = health_check.get("data_shape", [1, 1])[0] * health_check.get("data_shape", [1, 1])[1]
        missing_percentage = (missing_data.get("total_missing_values", 0) / total_cells) * 100
        score -= missing_percentage * 0.05  # -0.5 per 10% missing
        
        # Deduct for duplicates
        duplicate_percentage = health_check.get("data_quality", {}).get("duplicate_percentage", 0)
        score -= duplicate_percentage * 0.02  # -0.2 per 10% duplicates
        
        # Deduct for constant columns
        constant_cols = len(health_check.get("data_quality", {}).get("constant_columns", []))
        total_cols = health_check.get("data_shape", [1, 1])[1]
        score -= (constant_cols / total_cols) * 2  # -2 for all constant
        
        return max(0.0, min(10.0, score))
    
    def _calculate_cleaning_effectiveness(self, cleaning_report: Dict) -> float:
        """Calculate cleaning effectiveness score (0-10)."""
        if not cleaning_report:
            return 0.0
        
        summary = cleaning_report.get("cleaning_summary", {})
        reduction_percentage = summary.get("data_reduction_percentage", 0)
        
        # Good cleaning typically removes 5-30% of problematic data
        if 5 <= reduction_percentage <= 30:
            return 8.0 + (reduction_percentage - 15) * 0.1
        elif reduction_percentage < 5:
            return 5.0 + reduction_percentage
        else:  # > 30%
            return max(3.0, 10.0 - (reduction_percentage - 30) * 0.1)
    
    def save_results(self, analysis_results: Dict, output_path: str):
        """Save analysis results to a JSON file."""
        try:
            # Convert any non-serializable objects
            serializable_results = self._make_serializable(analysis_results)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_results, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Analysis results saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def _make_serializable(self, obj):
        """Convert objects to JSON-serializable format, including pandas/numpy types."""
        # Handle dict and list recursively
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]

        # Handle numpy types
        if self._is_numpy_int(obj):
            return int(obj)
        if self._is_numpy_float(obj):
            return float(obj)
        if self._is_numpy_bool(obj):
            return bool(obj)
        if self._is_numpy_array(obj):
            return obj.tolist()

        # Handle pandas types
        if self._is_pandas_series(obj):
            return obj.apply(self._make_serializable).to_dict()
        if self._is_pandas_dataframe(obj):
            return obj.applymap(self._make_serializable).to_dict(orient="list")
        if self._is_pandas_timestamp(obj):
            return obj.isoformat()
        if self._is_pandas_timedelta(obj):
            return str(obj)
        if self._is_pandas_categorical(obj):
            return obj.astype(str).tolist()
        if self._is_pandas_extension_dtype(obj):
            return str(obj)

        # Handle objects with to_dict or __dict__
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        if hasattr(obj, '__dict__'):
            return self._make_serializable(obj.__dict__)

        # Fallback: try to convert to string
        try:
            return str(obj)
        except Exception:
            return None

    def _is_numpy_int(self, obj):
        return isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8))

    def _is_numpy_float(self, obj):
        return isinstance(obj, (np.floating, np.float64, np.float32, np.float16))

    def _is_numpy_bool(self, obj):
        return isinstance(obj, (np.bool_, bool))

    def _is_numpy_array(self, obj):
        return isinstance(obj, (np.ndarray,))

    def _is_pandas_series(self, obj):
        import pandas as pd
        return isinstance(obj, pd.Series)

    def _is_pandas_dataframe(self, obj):
        import pandas as pd
        return isinstance(obj, pd.DataFrame)

    def _is_pandas_timestamp(self, obj):
        import pandas as pd
        return isinstance(obj, pd.Timestamp)

    def _is_pandas_timedelta(self, obj):
        import pandas as pd
        return isinstance(obj, pd.Timedelta)

    def _is_pandas_categorical(self, obj):
        import pandas as pd
        return isinstance(obj, pd.Categorical)

    def _is_pandas_extension_dtype(self, obj):
        import pandas as pd
        return isinstance(obj, pd.api.extensions.ExtensionDtype)


def main():
    """Example usage of the comprehensive analysis service."""
    print("🚀 Comprehensive Data Analysis Service")
    print("=" * 50)
    
    # Initialize the service
    try:
        service = ComprehensiveAnalysisService(use_openai=True)
        print("✅ Analysis service initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        return
    
    # Example file paths (update these with actual files)
    example_files = [
        "data/sample.csv",
        "data/report.xlsx",
        "data/dataset.tsv"
    ]
    
    print("\n📋 To analyze a file, use:")
    print("results = service.analyze_file('path/to/your/file.csv')")
    print("\n📋 For Excel files with multiple sheets:")
    print("results = service.analyze_file('path/to/file.xlsx', sheet_name='Sheet1')")
    print("\n📋 With custom cleaning configuration:")
    print("config = {'null_threshold': 0.3, 'outlier_method': 'isolation_forest'}")
    print("results = service.analyze_file('path/to/file.csv', cleaning_config=config)")
    
    print("\n💡 Example files to test (create these files first):")
    for file_path in example_files:
        print(f"   - {file_path}")
    
    # Uncomment to test with actual files:
    # results = service.analyze_file("path/to/your/data.csv")
    # service.save_results(results, "analysis_results.json")


if __name__ == "__main__":
    main()
