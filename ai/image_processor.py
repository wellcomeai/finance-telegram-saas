# ai/image_processor.py
"""
Image OCR processor for receipts using OpenAI Vision
"""

import logging
import json
import base64
from typing import Optional, Dict
from openai import AsyncOpenAI
from pathlib import Path
from datetime import datetime, timedelta

from ai.config import ai_config
from ai.prompts import prompts
from ai.categorizer import categorize_transaction

logger = logging.getLogger(__name__)


async def process_receipt_image(image_path: str) -> Optional[Dict]:
    """
    Process receipt image and extract transaction data
    
    Args:
        image_path: Path to image file
        
    Returns:
        Transaction data dictionary or None
    """
    try:
        logger.info(f"Processing receipt image: {image_path}")
        
        # Check file exists
        file_path = Path(image_path)
        if not file_path.exists():
            logger.error(f"Image file not found: {image_path}")
            return None
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > 20 * 1024 * 1024:  # 20MB limit
            logger.error(f"Image file too large: {file_size} bytes")
            return None
        
        logger.info(f"Image file size: {file_size} bytes")
        
        # Read and encode image
        with open(image_path, 'rb') as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Create prompt
        prompt = prompts.image_ocr_prompt()
        
        # Call OpenAI Vision
        async with AsyncOpenAI(api_key=ai_config.OPENAI_API_KEY) as client:
            response = await client.chat.completions.create(
                model=ai_config.VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=ai_config.VISION_MAX_TOKENS
            )
        
        # Extract response
        result_text = response.choices[0].message.content
        logger.info(f"Vision response: {result_text[:200]}")
        
        # Parse JSON
        receipt_data = _parse_receipt_json(result_text)
        
        if not receipt_data:
            logger.error("Failed to parse receipt data")
            return None
        
        # Convert to transaction format
        transaction_data = await _receipt_to_transaction(receipt_data)
        
        if transaction_data:
            logger.info(f"Successfully processed receipt: {transaction_data['amount']} ₽")
        
        return transaction_data
        
    except Exception as e:
        logger.error(f"Error processing receipt image: {e}", exc_info=True)
        return None


def _parse_receipt_json(text: str) -> Optional[Dict]:
    """Parse JSON from receipt OCR response"""
    try:
        # Remove markdown if present
        text = text.strip()
        if text.startswith('```'):
            # Remove ```json or ```
            lines = text.split('\n')
            if lines[0].strip().startswith('```'):
                text = '\n'.join(lines[1:])
        if text.endswith('```'):
            lines = text.split('\n')
            if lines[-1].strip() == '```':
                text = '\n'.join(lines[:-1])
        
        text = text.strip()
        
        data = json.loads(text)
        
        # Validate required fields
        if 'amount' not in data or data['amount'] is None:
            logger.error("Missing amount in receipt data")
            return None
        
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        logger.error(f"Text was: {text}")
        return None
    except Exception as e:
        logger.error(f"Error parsing receipt JSON: {e}")
        return None


async def _receipt_to_transaction(receipt_data: Dict) -> Optional[Dict]:
    """
    Convert receipt data to transaction format
    """
    try:
        # Extract amount
        amount = float(receipt_data['amount'])
        if amount <= 0:
            logger.error(f"Invalid amount: {amount}")
            return None
        
        # Build description
        description_parts = []
        if receipt_data.get('merchant'):
            description_parts.append(receipt_data['merchant'])
        if receipt_data.get('items'):
            items_str = ', '.join(receipt_data['items'][:3])  # First 3 items
            description_parts.append(items_str)
        
        description = ' - '.join(description_parts) if description_parts else 'Покупка по чеку'
        description = description[:200]  # Limit length
        
        # Parse and validate date
        date_str = receipt_data.get('date')
        transaction_date = datetime.now().date()  # Default to today
        
        if date_str:
            try:
                parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # ВАЛИДАЦИЯ: проверяем адекватность даты
                days_difference = (datetime.now().date() - parsed_date).days
                
                # Если дата старше 30 дней или в будущем - используем сегодня
                if days_difference > 30:
                    logger.warning(
                        f"Receipt date {date_str} is {days_difference} days ago (too old). "
                        f"Using current date instead."
                    )
                    transaction_date = datetime.now().date()
                elif days_difference < 0:
                    logger.warning(
                        f"Receipt date {date_str} is in the future ({abs(days_difference)} days ahead). "
                        f"Using current date instead."
                    )
                    transaction_date = datetime.now().date()
                else:
                    # Дата адекватная - используем её
                    transaction_date = parsed_date
                    logger.info(f"Using receipt date: {date_str}")
                    
            except ValueError:
                logger.warning(f"Invalid date format: {date_str}, using today")
                transaction_date = datetime.now().date()
        else:
            logger.info("No date in receipt, using today")
        
        # Categorize
        category = await categorize_transaction(description, amount, 'expense')
        
        # Build result
        result = {
            'type': 'expense',  # Receipts are always expenses
            'amount': amount,
            'category_name': category['name'],
            'category_icon': category['icon'],
            'description': description,
            'date': transaction_date
        }
        
        logger.info(f"Receipt converted to transaction: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error converting receipt to transaction: {e}", exc_info=True)
        return None


async def download_photo_file(bot, file_id: str, destination: str) -> bool:
    """
    Download photo from Telegram
    
    Args:
        bot: Telegram bot instance
        file_id: Telegram file ID
        destination: Path where to save file
        
    Returns:
        True if successful
    """
    try:
        file = await bot.get_file(file_id)
        logger.info(f"Downloading photo: {file.file_path}, size: {file.file_size} bytes")
        
        await bot.download_file(file.file_path, destination)
        logger.info(f"Photo downloaded to {destination}")
        return True
        
    except Exception as e:
        logger.error(f"Error downloading photo: {e}", exc_info=True)
        return False
