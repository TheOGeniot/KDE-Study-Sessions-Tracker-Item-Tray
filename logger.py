#!/usr/bin/env python3
"""
Centralized logging for Study Session Manager
Logs are stored in ~/.local/share/study-session/logs/
"""

import logging
from pathlib import Path
from datetime import datetime


def setup_logger(name: str, level=logging.INFO) -> logging.Logger:
    """Create a logger that writes to both file and console"""
    log_dir = Path.home() / '.local/share/study-session' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create log file with date
    log_file = log_dir / f"session_manager_{datetime.now().strftime('%Y%m%d')}.log"
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # File handler - detailed logs
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler - important messages only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
