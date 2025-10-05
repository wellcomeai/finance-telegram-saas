"""
Text transaction parser using OpenAI GPT-5
"""

import logging
import json
from typing import Optional, Dict
from openai import AsyncOpenAI
from datetime import datetime

from ai.config import ai_config
from ai.prompts import prompts
from shared.constants import CATEGORIES

logger = logging.getLogger(__name__)


async def parse_transaction_text(text: str) -> Optional[Dict]:
    """
    Parse transaction from text using GPT-5
    
    Args:
        text: User's text message
        
    Returns:
        Dictionary with transaction data or None if parsing failed
        {
            'type': 'income' or 'expense',
            'amount': float,
            'category_name': str,
            'category_icon': str,
            'description': str,
            'date': date object
        }
    """
    if not text or len(text.strip()) < 3:
        logger.warning("Text too short for parsing")
        return None
    
    try:
        logger.info(f"Parsing transaction text: {text[:50]}...")
        
        # Create prompt
        prompt = prompts.text_parser_prompt(text)
        
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
                max_completion_tokens=ai_config.MAX_TOKENS
                # temperature removed - GPT-5 only supports default (1)
            )
        
        # Extract result
        result_text = response.choices[0].message.content
        
        if not result_text:
            logger.error("Empty response from GPT-5")
            return None
        
        logger.info(f"GPT-5 response: {result_text[:200]}")
        
        # Parse JSON
        transaction_data = _parse_json_response(result_text)
        
        if not transaction_data:
            logger.error("Failed to parse JSON from GPT response")
            return None
        
        # Validate and enrich data
        validated_data = _validate_and_enrich(transaction_data)
        
        if validated_data:
            logger.info(f"Successfully parsed transaction: {validated_data['type']} {validated_data['amount']} ₽")
        
        return validated_data
        
    except Exception as e:
        logger.error(f"Error parsing transaction text: {e}", exc_info=True)
        return None


def _parse_json_response(text: str) -> Optional[Dict]:
    """
    Parse JSON from GPT response (handling markdown code blocks)
    """
    try:
        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith('```'):
            # Remove ```json or ```
            text = text.split('\n', 1)[1] if '\n' in text else text[3:]
        if text.endswith('```'):
            text = text.rsplit('\n', 1)[0] if '\n' in text else text[:-3]
        
        text = text.strip()
        
        # Parse JSON
        data = json.loads(text)
        
        # Validate required fields
        required_fields = ['type', 'amount', 'category_name']
        if not all(field in data for field in required_fields):
            logger.error(f"Missing required fields in JSON: {data}")
            return None
        
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}. Text: {text}")
        return None
    except Exception as e:
        logger.error(f"Error parsing JSON response: {e}")
        return None


def _validate_and_enrich(data: Dict) -> Optional[Dict]:
    """
    Validate and enrich transaction data
    """
    try:
        # Validate type
        if data['type'] not in ['income', 'expense']:
            logger.error(f"Invalid transaction type: {data['type']}")
            return None
        
        # Validate and convert amount
        try:
            amount = float(data['amount'])
            if amount <= 0:
                logger.error(f"Invalid amount: {amount}")
                return None
        except (ValueError, TypeError):
            logger.error(f"Cannot convert amount to float: {data['amount']}")
            return None
        
        # Find category and get icon
        category_name = data['category_name']
        category = next(
            (cat for cat in CATEGORIES if cat['name'].lower() == category_name.lower()),
            None
        )
        
        if not category:
            logger.warning(f"Category not found: {category_name}, using default")
            # Use default category based on type
            if data['type'] == 'expense':
                category = next(cat for cat in CATEGORIES if cat['name'] == 'Прочее')
            else:
                category = next(cat for cat in CATEGORIES if cat['name'] == 'Другие доходы')
        
        # Parse date
        date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        try:
            transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}, using today")
            transaction_date = datetime.now().date()
        
        # Build result
        result = {
            'type': data['type'],
            'amount': amount,
            'category_name': category['name'],
            'category_icon': category['icon'],
            'description': data.get('description', '')[:200],  # Limit description length
            'date': transaction_date
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating transaction data: {e}")
        return None
