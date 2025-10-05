"""
Utility functions
"""

import re
from typing import Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation

from shared.constants import CURRENCY_SYMBOL, DATE_FORMAT, DISPLAY_DATE_FORMAT


def format_amount(amount: float, with_currency: bool = True) -> str:
    """
    Format amount for display
    
    Args:
        amount: Amount to format
        with_currency: Include currency symbol
        
    Returns:
        Formatted string (e.g., "1 500.00 ₽")
    """
    formatted = f"{amount:,.2f}".replace(",", " ")
    
    if with_currency:
        return f"{formatted} {CURRENCY_SYMBOL}"
    
    return formatted


def parse_amount(text: str) -> Optional[float]:
    """
    Parse amount from text
    
    Args:
        text: Text containing amount
        
    Returns:
        Parsed amount or None if invalid
    """
    try:
        # Remove currency symbols and spaces
        cleaned = re.sub(r'[₽$€\s,]', '', text)
        
        # Replace comma with dot for decimal
        cleaned = cleaned.replace(',', '.')
        
        # Try to convert to float
        amount = float(cleaned)
        
        # Validate
        if amount <= 0 or amount > 1_000_000_000:
            return None
        
        return round(amount, 2)
        
    except (ValueError, InvalidOperation):
        return None


def validate_date(date_str: str, date_format: str = DISPLAY_DATE_FORMAT) -> Optional[date]:
    """
    Validate and parse date string
    
    Args:
        date_str: Date string to parse
        date_format: Expected date format
        
    Returns:
        date object or None if invalid
    """
    try:
        parsed_date = datetime.strptime(date_str, date_format).date()
        
        # Check if date is not in the future
        if parsed_date > date.today():
            return None
        
        # Check if date is not too old (10 years)
        min_date = date.today() - timedelta(days=365 * 10)
        if parsed_date < min_date:
            return None
        
        return parsed_date
        
    except ValueError:
        return None


def get_date_range(period: str = 'month') -> Tuple[date, date]:
    """
    Get date range for common periods
    
    Args:
        period: 'week', 'month', 'year', or 'all'
        
    Returns:
        Tuple of (start_date, end_date)
    """
    today = date.today()
    
    if period == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif period == 'month':
        start_date = today.replace(day=1)
        end_date = today
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif period == 'all':
        start_date = date(2020, 1, 1)
        end_date = today
    else:
        # Default to current month
        start_date = today.replace(day=1)
        end_date = today
    
    return start_date, end_date


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # Remove potentially dangerous characters
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text:
        return ''
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def get_month_name(month: int) -> str:
    """
    Get Russian month name
    
    Args:
        month: Month number (1-12)
        
    Returns:
        Month name in Russian
    """
    month_names = {
        1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
        5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
        9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
    }
    return month_names.get(month, 'Неизвестно')


def get_weekday_name(weekday: int) -> str:
    """
    Get Russian weekday name
    
    Args:
        weekday: Weekday number (0=Monday, 6=Sunday)
        
    Returns:
        Weekday name in Russian
    """
    weekday_names = {
        0: 'Понедельник', 1: 'Вторник', 2: 'Среда', 3: 'Четверг',
        4: 'Пятница', 5: 'Суббота', 6: 'Воскресенье'
    }
    return weekday_names.get(weekday, 'Неизвестно')


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change
    
    Args:
        old_value: Old value
        new_value: New value
        
    Returns:
        Percentage change (e.g., 15.5 for 15.5% increase)
    """
    if old_value == 0:
        return 0.0
    
    change = ((new_value - old_value) / old_value) * 100
    return round(change, 2)


def is_valid_telegram_user_id(user_id: int) -> bool:
    """
    Validate Telegram user ID
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        True if valid
    """
    # Telegram user IDs are positive integers typically > 0
    return isinstance(user_id, int) and user_id > 0


def chunk_list(items: list, chunk_size: int) -> list:
    """
    Split list into chunks
    
    Args:
        items: List to split
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero
        
    Returns:
        Result or default
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default
