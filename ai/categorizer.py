"""
Transaction categorizer using AI
"""

import logging
from typing import Dict
from openai import AsyncOpenAI

from ai.config import ai_config
from ai.prompts import prompts
from shared.constants import CATEGORIES

logger = logging.getLogger(__name__)


async def categorize_transaction(description: str, amount: float, transaction_type: str) -> Dict:
    """
    Categorize transaction using AI
    
    Args:
        description: Transaction description
        amount: Transaction amount
        transaction_type: 'income' or 'expense'
        
    Returns:
        Category dictionary with 'name' and 'icon'
    """
    try:
        logger.info(f"Categorizing transaction: {description} ({transaction_type})")
        
        # Create prompt
        prompt = prompts.categorizer_prompt(description, amount, transaction_type)
        
        # Call OpenAI GPT-5
        async with AsyncOpenAI(api_key=ai_config.OPENAI_API_KEY) as client:
            response = await client.chat.completions.create(
                model=ai_config.GPT_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_completion_tokens=50  # Short response
                # temperature removed - GPT-5 only supports default (1)
            )
        
        # Extract category name
        category_name = response.choices[0].message.content
        
        if not category_name:
            logger.warning("Empty category response, using default")
            return _get_default_category(transaction_type)
        
        category_name = category_name.strip()
        logger.info(f"AI suggested category: {category_name}")
        
        # Find category in CATEGORIES
        category = next(
            (cat for cat in CATEGORIES 
             if cat['name'].lower() == category_name.lower() and cat['type'] == transaction_type),
            None
        )
        
        if category:
            return {'name': category['name'], 'icon': category['icon']}
        
        # Fallback to default
        logger.warning(f"Category not found: {category_name}, using default")
        return _get_default_category(transaction_type)
        
    except Exception as e:
        logger.error(f"Error categorizing transaction: {e}")
        return _get_default_category(transaction_type)


def _get_default_category(transaction_type: str) -> Dict:
    """Get default category based on transaction type"""
    if transaction_type == 'expense':
        default = next(cat for cat in CATEGORIES if cat['name'] == 'Прочее')
    else:
        default = next(cat for cat in CATEGORIES if cat['name'] == 'Другие доходы')
    
    return {'name': default['name'], 'icon': default['icon']}
