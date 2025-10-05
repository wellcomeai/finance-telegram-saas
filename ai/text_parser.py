"""
Text transaction parser using OpenAI GPT-5
"""

import logging
import json
from typing import List, Dict
from openai import AsyncOpenAI
from datetime import datetime

from ai.config import ai_config
from ai.prompts import prompts
from shared.constants import CATEGORIES

logger = logging.getLogger(__name__)


async def parse_transaction_text(text: str) -> List[Dict]:
    """
    Parse transaction(s) from text using GPT-5
    
    Args:
        text: User's text message
        
    Returns:
        List of transaction dictionaries (может быть пустым списком)
        Each transaction:
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
        return []
    
    try:
        logger.info(f"Parsing transaction text: {text[:100]}...")
        
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
            return []
        
        logger.info(f"GPT-5 response: {result_text[:300]}")
        
        # Parse JSON array
        transactions_data = _parse_json_response(result_text)
        
        if not transactions_data:
            logger.error("Failed to parse JSON from GPT response")
            return []
        
        # Validate and enrich each transaction
        validated_transactions = []
        
        for idx, transaction_data in enumerate(transactions_data, 1):
            validated = _validate_and_enrich(transaction_data)
            if validated:
                validated_transactions.append(validated)
                logger.info(
                    f"Transaction {idx}/{len(transactions_data)}: "
                    f"{validated['type']} {validated['amount']} ₽ - {validated['description']}"
                )
            else:
                logger.warning(f"Failed to validate transaction {idx}: {transaction_data}")
        
        if validated_transactions:
            logger.info(f"Successfully parsed {len(validated_transactions)} transaction(s)")
        else:
            logger.warning("No valid transactions found")
        
        return validated_transactions
        
    except Exception as e:
        logger.error(f"Error parsing transaction text: {e}", exc_info=True)
        return []


def _parse_json_response(text: str) -> List[Dict]:
    """
    Parse JSON array from GPT response (handling markdown code blocks)
    
    Returns:
        List of transaction dictionaries or empty list
    """
    try:
        # Remove markdown code blocks if present
        text = text.strip()
        
        # Remove ```json or ``` at start
        if text.startswith('```'):
            lines = text.split('\n')
            # Skip first line (```json or ```)
            text = '\n'.join(lines[1:])
        
        # Remove ``` at end
        if text.endswith('```'):
            lines = text.split('\n')
            # Remove last line if it's ```
            if lines[-1].strip() == '```':
                text = '\n'.join(lines[:-1])
        
        text = text.strip()
        
        # Parse JSON
        data = json.loads(text)
        
        # Ensure it's a list
        if not isinstance(data, list):
            logger.error(f"Expected JSON array, got: {type(data)}")
            return []
        
        # Validate each transaction has required fields
        required_fields = ['type', 'amount', 'category_name']
        valid_transactions = []
        
        for idx, transaction in enumerate(data):
            if not isinstance(transaction, dict):
                logger.warning(f"Transaction {idx} is not a dict: {transaction}")
                continue
            
            if all(field in transaction for field in required_fields):
                valid_transactions.append(transaction)
            else:
                missing = [f for f in required_fields if f not in transaction]
                logger.warning(f"Transaction {idx} missing fields: {missing}")
        
        return valid_transactions
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}. Text: {text[:200]}")
        return []
    except Exception as e:
        logger.error(f"Error parsing JSON response: {e}")
        return []


def _validate_and_enrich(data: Dict) -> Dict | None:
    """
    Validate and enrich single transaction data
    
    Returns:
        Validated transaction dict or None if invalid
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
            
            # Валидация даты (не слишком старая, не в будущем)
            days_diff = (datetime.now().date() - transaction_date).days
            if days_diff > 365:
                logger.warning(f"Date too old ({date_str}), using today")
                transaction_date = datetime.now().date()
            elif days_diff < 0:
                logger.warning(f"Date in future ({date_str}), using today")
                transaction_date = datetime.now().date()
                
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
        logger.error(f"Error validating transaction data: {e}", exc_info=True)
        return None
