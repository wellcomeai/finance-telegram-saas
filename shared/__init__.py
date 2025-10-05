"""
Shared Module
Common utilities, configuration, and constants
"""

from .config import settings
from .constants import CATEGORIES, TRANSACTION_TYPES, CATEGORY_ICONS
from .logger import setup_logging, get_logger
from .utils import format_amount, parse_amount, validate_date, get_date_range

__version__ = "1.0.0"

__all__ = [
    "settings",
    "CATEGORIES",
    "TRANSACTION_TYPES",
    "CATEGORY_ICONS",
    "setup_logging",
    "get_logger",
    "format_amount",
    "parse_amount",
    "validate_date",
    "get_date_range"
]
