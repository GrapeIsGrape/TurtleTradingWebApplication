"""
Script Logging Utilities

Common logging functions used across trading scripts for consistent
log formatting, file handling, and directory management.
"""

import os
from datetime import datetime
from pathlib import Path


def get_script_directory() -> str:
    """
    Get the absolute path to the script directory.
    
    Returns:
        String path to the script directory with trailing slash
    """
    return os.path.dirname(os.path.abspath(__file__)) + '/'


def get_log_file_path(script_dir: str, log_folder: str, log_file_name: str) -> Path:
    """
    Get the full path to a log file, creating directory if needed.
    
    Args:
        script_dir: Base script directory
        log_folder: Relative path to log folder (e.g., 'script_logs')
        log_file_name: Name of the log file
        
    Returns:
        Path object pointing to the log file
    """
    log_path = Path(script_dir) / log_folder / log_file_name
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return log_path


def log_message(file_path: Path, level: str, message: str) -> None:
    """
    Write a timestamped log message to file.
    
    Args:
        file_path: Path to log file
        level: Log level (START, INFO, END, ERROR, WARN, etc.)
        message: Log message content
    """
    with open(file_path, 'a') as f:
        f.write(f'[{level:6}] {str(datetime.now())} {message}\n')
