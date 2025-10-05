"""
Data models (dataclasses) for database entities
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from decimal import Decimal


@dataclass
class User:
    """User model"""
    id: int
    telegram_user_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or self.username or f"User {self.telegram_user_id}"


@dataclass
class Category:
    """Category model"""
    id: int
    name: str
    icon: str
    type: str  # 'income' or 'expense'
    is_active: bool
    
    def __str__(self) -> str:
        return f"{self.icon} {self.name}"


@dataclass
class Transaction:
    """Transaction model"""
    id: int
    user_id: int
    type: str  # 'income' or 'expense'
    amount: Decimal
    category_id: Optional[int]
    description: Optional[str]
    transaction_date: date
    created_at: datetime
    updated_at: datetime
    
    # Related data (loaded separately)
    category: Optional[Category] = None
    
    @property
    def amount_float(self) -> float:
        """Get amount as float"""
        return float(self.amount)
    
    @property
    def formatted_amount(self) -> str:
        """Get formatted amount string"""
        return f"{self.amount:,.2f} ₽".replace(",", " ")
    
    def __str__(self) -> str:
        type_emoji = "💸" if self.type == "expense" else "💰"
        return f"{type_emoji} {self.formatted_amount} - {self.description}"
