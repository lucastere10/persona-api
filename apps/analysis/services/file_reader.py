"""
File Reader Service for Data Analysis

This service handles reading various file formats (CSV, Excel, etc.)
and provides worksheet detection and data loading capabilities.
"""

import pandas as pd
import io
import mimetypes
from typing import Dict, List, Tuple, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FileReader:
    """
    Service for reading and processing various data file formats.
    Supports CSV, Excel (XLS/XLSX), and provides worksheet detection.
    """
    
    SUPPORTED_FORMATS = {
        'csv': ['.csv'],
        'excel': ['.xls', '.xlsx', '.xlsm'],
        'text': ['.txt', '.tsv']
    }
    
    def __init__(self):
        self.file_info = {}
    
    def detect_file_type(self, filename: str) -> str:
        """
        Detect the file type based on extension and content.
        
        Args:
            filename: Name of the file
            
        Returns:
            str: File type ('csv', 'excel', 'text', 'unknown')
        """
        file_extension = Path(filename).suffix.lower()
        
        # Check by extension first
        for file_type, extensions in self.SUPPORTED_FORMATS.items():
            if file_extension in extensions:
                return file_type
        
        # If extension is unknown, try to detect by content
        try:
            # Try to detect by MIME type
            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type:
                if 'csv' in mime_type or 'text' in mime_type:
                    return 'text'
                elif 'spreadsheet' in mime_type or 'excel' in mime_type:
                    return 'excel'
        except Exception as e:
            logger.warning(f"Could not detect MIME type: {e}")
        
        return 'unknown'
    
    def get_excel_worksheets(self, file_obj, filename: str) -> List[str]:
        """
        Get list of worksheet names from an Excel file.
        
        Args:
            file_obj: Excel file object
            filename: Name of the file
            
        Returns:
            List[str]: List of worksheet names
        """
        try:
            # Reset file pointer if it's a file object
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            
            # Read Excel file metadata
            excel_file = pd.ExcelFile(file_obj)
            worksheets = excel_file.sheet_names
            
            logger.info(f"Found {len(worksheets)} worksheets in {filename}: {worksheets}")
            return worksheets
            
        except Exception as e:
            logger.error(f"Error reading Excel worksheets from {filename}: {e}")
            raise ValueError(f"Could not read Excel file: {e}")
    
    def _prepare_file_for_reading(self, file_obj):
        """
        Prepare file object for reading by converting to appropriate format.
        
        Args:
            file_obj: File object to prepare
            
        Returns:
            file object: Prepared file object (BytesIO or StringIO)
        """
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        
        if hasattr(file_obj, 'read'):
            content = file_obj.read()
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            # Convert to BytesIO for consistent handling
            import io
            if isinstance(content, bytes):
                return io.BytesIO(content)
            else:
                return io.StringIO(content)
        
        return file_obj
    
    def _try_csv_with_params(self, file_obj, params):
        """
        Try reading CSV with specific parameters.
        
        Args:
            file_obj: File object
            params: Parameters for pandas read_csv
            
        Returns:
            pd.DataFrame or None: DataFrame if successful, None otherwise
        """
        try:
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            return pd.read_csv(file_obj, **params)
        except Exception:
            return None
    
    def read_csv_file(self, file_obj, filename: str, **kwargs) -> pd.DataFrame:
        """
        Read CSV file with intelligent delimiter detection.
        
        Args:
            file_obj: CSV file object
            filename: Name of the file
            **kwargs: Additional pandas read_csv parameters
            
        Returns:
            pd.DataFrame: Loaded data
        """
        try:
            # Prepare file object
            prepared_file = self._prepare_file_for_reading(file_obj)
            
            # Base parameters
            base_params = {
                'encoding': 'utf-8',
                'on_bad_lines': 'skip'
            }
            base_params.update(kwargs)
            
            # Try comma separator with C engine first (most common)
            csv_params = base_params.copy()
            csv_params.update({'sep': ',', 'engine': 'c'})
            
            df = self._try_csv_with_params(prepared_file, csv_params)
            if df is not None and (df.shape[1] > 1 or (df.shape[1] == 1 and df.shape[0] > 0)):
                logger.info(f"Successfully loaded CSV {filename} with comma separator: {df.shape}")
                return df
            
            # Try auto-detection with python engine
            csv_params = base_params.copy()
            csv_params.update({'sep': None, 'engine': 'python'})
            
            df = self._try_csv_with_params(prepared_file, csv_params)
            if df is not None:
                logger.info(f"Successfully loaded CSV {filename} with auto-detection: {df.shape}")
                return df
            
            raise ValueError("Could not parse CSV with standard methods")
            
        except UnicodeDecodeError:
            return self._try_alternative_encodings(prepared_file, filename, base_params)
        except Exception as e:
            logger.error(f"Error reading CSV file {filename}: {e}")
            raise ValueError(f"Could not read CSV file: {e}")
    
    def _try_alternative_encodings(self, file_obj, filename: str, base_params: dict) -> pd.DataFrame:
        """
        Try reading CSV with alternative encodings.
        
        Args:
            file_obj: File object
            filename: Filename for logging
            base_params: Base parameters for CSV reading
            
        Returns:
            pd.DataFrame: Successfully loaded DataFrame
        """
        encodings = ['latin-1', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings:
            csv_params = base_params.copy()
            csv_params.update({
                'encoding': encoding,
                'sep': ',',
                'engine': 'c'
            })
            
            df = self._try_csv_with_params(file_obj, csv_params)
            if df is not None:
                logger.info(f"Successfully loaded CSV {filename} with {encoding} encoding: {df.shape}")
                return df
        
        raise ValueError(f"Could not decode CSV file {filename} with any supported encoding")
    
    def read_excel_file(self, file_obj, filename: str, sheet_name: Optional[str] = None, **kwargs) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        Read Excel file, optionally specifying worksheet.
        
        Args:
            file_obj: Excel file object
            filename: Name of the file
            sheet_name: Specific sheet name to read (None reads all sheets)
            **kwargs: Additional pandas read_excel parameters
            
        Returns:
            pd.DataFrame or Dict[str, pd.DataFrame]: Loaded data
        """
        try:
            # Reset file pointer
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            
            # Default parameters
            excel_params = {
                'engine': 'openpyxl' if filename.endswith('.xlsx') else 'xlrd'
            }
            excel_params.update(kwargs)
            
            if sheet_name:
                # Read specific sheet
                df = pd.read_excel(file_obj, sheet_name=sheet_name, **excel_params)
                logger.info(f"Successfully loaded Excel sheet '{sheet_name}' from {filename}: {df.shape}")
                return df
            else:
                # Read all sheets
                dfs = pd.read_excel(file_obj, sheet_name=None, **excel_params)
                logger.info(f"Successfully loaded {len(dfs)} sheets from Excel file {filename}")
                return dfs
            
        except Exception as e:
            logger.error(f"Error reading Excel file {filename}: {e}")
            raise ValueError(f"Could not read Excel file: {e}")
    
    def read_text_file(self, file_obj, filename: str, delimiter: str = '\t', **kwargs) -> pd.DataFrame:
        """
        Read text file (TSV, tab-delimited, etc.).
        
        Args:
            file_obj: Text file object
            filename: Name of the file
            delimiter: Field delimiter
            **kwargs: Additional pandas read_csv parameters
            
        Returns:
            pd.DataFrame: Loaded data
        """
        try:
            # Reset file pointer
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            
            # Parameters for text files
            text_params = {
                'sep': delimiter,
                'encoding': 'utf-8',
                'engine': 'python',
                'on_bad_lines': 'skip'
            }
            text_params.update(kwargs)
            
            df = pd.read_csv(file_obj, **text_params)
            logger.info(f"Successfully loaded text file {filename}: {df.shape}")
            return df
            
        except Exception as e:
            logger.error(f"Error reading text file {filename}: {e}")
            raise ValueError(f"Could not read text file: {e}")
    
    def read_file(self, file_obj, filename: str, sheet_name: Optional[str] = None, **kwargs) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        Main method to read any supported file format.
        
        Args:
            file_obj: File object
            filename: Name of the file
            sheet_name: For Excel files, specific sheet to read
            **kwargs: Additional parameters for specific readers
            
        Returns:
            pd.DataFrame or Dict[str, pd.DataFrame]: Loaded data
        """
        file_type = self.detect_file_type(filename)
        
        if file_type == 'csv':
            return self.read_csv_file(file_obj, filename, **kwargs)
        elif file_type == 'excel':
            return self.read_excel_file(file_obj, filename, sheet_name=sheet_name, **kwargs)
        elif file_type == 'text':
            return self.read_text_file(file_obj, filename, **kwargs)
        else:
            raise ValueError(f"Unsupported file type: {file_type} for file {filename}")
    
    def get_file_info(self, file_obj, filename: str) -> Dict:
        """
        Get comprehensive information about a file.
        
        Args:
            file_obj: File object
            filename: Name of the file
            
        Returns:
            Dict: File information including type, size, worksheets (if Excel)
        """
        file_type = self.detect_file_type(filename)
        
        info = {
            'filename': filename,
            'file_type': file_type,
            'supported': file_type != 'unknown'
        }
        
        # Get file size if possible
        try:
            if hasattr(file_obj, 'size'):
                info['size'] = file_obj.size
            elif hasattr(file_obj, 'seek') and hasattr(file_obj, 'tell'):
                current_pos = file_obj.tell()
                file_obj.seek(0, 2)  # Seek to end
                info['size'] = file_obj.tell()
                file_obj.seek(current_pos)  # Reset position
        except Exception:
            info['size'] = None
        
        # For Excel files, get worksheet information
        if file_type == 'excel':
            try:
                info['worksheets'] = self.get_excel_worksheets(file_obj, filename)
            except Exception as e:
                info['worksheets'] = []
                info['error'] = str(e)
        
        return info
    
    def validate_data(self, df: pd.DataFrame) -> Dict:
        """
        Perform basic validation on loaded data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Dict: Validation results
        """
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'shape': df.shape,
            'empty_data': df.empty,
            'duplicate_rows': df.duplicated().sum(),
            'columns_with_nulls': df.isnull().any().sum(),
            'total_nulls': df.isnull().sum().sum()
        }
        
        # Check for common issues
        if df.empty:
            validation['is_valid'] = False
            validation['errors'].append("Data is empty")
        
        if df.shape[1] == 1 and df.shape[0] > 1:
            validation['warnings'].append("Data might have delimiter detection issues (only 1 column)")
        
        if validation['duplicate_rows'] > 0:
            validation['warnings'].append(f"Found {validation['duplicate_rows']} duplicate rows")
        
        if validation['total_nulls'] > df.size * 0.5:
            validation['warnings'].append("More than 50% of data contains null values")
        
        return validation


# Utility functions for common operations
def read_data_file(file_obj, filename: str, sheet_name: Optional[str] = None) -> Tuple[Union[pd.DataFrame, Dict[str, pd.DataFrame]], Dict]:
    """
    Convenience function to read a data file and get validation info.
    
    Args:
        file_obj: File object
        filename: Name of the file
        sheet_name: For Excel files, specific sheet to read
        
    Returns:
        Tuple[data, validation_info]: Loaded data and validation results
    """
    reader = FileReader()
    
    # Get file info
    file_info = reader.get_file_info(file_obj, filename)
    
    if not file_info['supported']:
        raise ValueError(f"File type not supported: {file_info['file_type']}")
    
    # Read the data
    data = reader.read_file(file_obj, filename, sheet_name=sheet_name)
    
    # Validate if it's a single DataFrame
    validation_info = file_info
    if isinstance(data, pd.DataFrame):
        validation_info.update(reader.validate_data(data))
    
    return data, validation_info


def get_excel_info(file_obj, filename: str) -> Dict:
    """
    Get detailed information about an Excel file including all worksheets.
    
    Args:
        file_obj: Excel file object
        filename: Name of the file
        
    Returns:
        Dict: Information about the Excel file and its worksheets
    """
    reader = FileReader()
    
    if reader.detect_file_type(filename) != 'excel':
        raise ValueError("File is not an Excel file")
    
    worksheets = reader.get_excel_worksheets(file_obj, filename)
    
    info = {
        'filename': filename,
        'total_worksheets': len(worksheets),
        'worksheets': []
    }
    
    # Get info for each worksheet
    for sheet_name in worksheets:
        try:
            df = reader.read_excel_file(file_obj, filename, sheet_name=sheet_name)
            validation = reader.validate_data(df)
            
            sheet_info = {
                'name': sheet_name,
                'shape': df.shape,
                'columns': list(df.columns),
                'validation': validation
            }
            info['worksheets'].append(sheet_info)
            
        except Exception as e:
            info['worksheets'].append({
                'name': sheet_name,
                'error': str(e)
            })
    
    return info
