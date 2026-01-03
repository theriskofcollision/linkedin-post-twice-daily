"""
Structured logging configuration for LinkedIn Growth Workflow.
Provides log levels, formatting, and sensitive data filtering.
"""

import logging
import sys
import re
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in log messages."""
    
    PATTERNS = [
        (r'Bearer [A-Za-z0-9\-_]+', 'Bearer [REDACTED]'),
        (r'api_key["\']?\s*[:=]\s*["\']?[A-Za-z0-9\-_]+', 'api_key=[REDACTED]'),
        (r'token["\']?\s*[:=]\s*["\']?[A-Za-z0-9\-_]+', 'token=[REDACTED]'),
        (r'urn:li:person:[A-Za-z0-9\-_]+', 'urn:li:person:[REDACTED]'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = re.sub(pattern, replacement, record.msg, flags=re.IGNORECASE)
        return True


def setup_logging(
    level: str = "INFO",
    name: str = "linkedin_workflow"
) -> logging.Logger:
    """
    Configure structured logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Console handler with formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Format: timestamp - level - module - message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    
    # Add sensitive data filter
    console_handler.addFilter(SensitiveDataFilter())
    
    logger.addHandler(console_handler)
    
    return logger


# Create default logger instance
logger = setup_logging()
