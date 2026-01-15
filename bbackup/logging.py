"""
Logging setup for bbackup.
Implements file logging with rotation based on configuration.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .config import Config


def setup_logging(config: Config) -> logging.Logger:
    """
    Setup logging system based on configuration.
    
    Args:
        config: Configuration object with logging settings
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('bbackup')
    
    # Don't add handlers if they already exist (avoid duplicates)
    if logger.handlers:
        return logger
    
    # Set log level from config
    log_level_str = config.data.get('logging', {}).get('level', 'INFO')
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Get log file path from config
    log_file_str = config.data.get('logging', {}).get('file', '~/.local/share/bbackup/bbackup.log')
    log_file = Path(log_file_str).expanduser()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create rotating file handler
    max_bytes = config.data.get('logging', {}).get('max_size_mb', 10) * 1024 * 1024
    backup_count = config.data.get('logging', {}).get('backup_count', 5)
    
    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    
    # Set formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    # Also add console handler for important messages
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get logger instance.
    
    Args:
        name: Optional logger name (defaults to 'bbackup')
    
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f'bbackup.{name}')
    return logging.getLogger('bbackup')
