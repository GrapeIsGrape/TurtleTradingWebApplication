"""File I/O utilities for CSV operations."""

from typing import List
from pathlib import Path
import pandas as pd


def save_csv(df: pd.DataFrame, path: str, file_name: str) -> None:
    """
    Save DataFrame to CSV file.
    
    Args:
        df: DataFrame to save
        path: Directory path (with trailing slash)
        file_name: Name of the file including .csv extension
    """
    full_path = Path(path) / file_name
    full_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(full_path, index=False, encoding='utf-8')


def read_file_names_in_path(path: str) -> List[str]:
    """
    Get list of file names (without extensions) in a directory.
    
    Args:
        path: Directory path to scan
        
    Returns:
        List of file names without extensions
    """
    path_obj = Path(path)
    if not path_obj.exists():
        return []
    
    return [
        file.stem 
        for file in path_obj.iterdir() 
        if file.is_file() and not file.name.startswith('.')
    ]
