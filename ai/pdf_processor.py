"""
PDF receipt processor
"""

import logging
import json
from typing import Optional, Dict
from openai import AsyncOpenAI
from pathlib import Path
from datetime import datetime
import PyPDF2

from ai.config import ai_config
from ai.prompts import prompts
from ai.categorizer import categorize_transaction

logger = logging.getLogger(__name__)


async def process_receipt_pdf(pdf_path: str) -> Optional[Dict]:
    """
    Process PDF receipt and extract transaction data
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Transaction data dictionary or None
    """
    try:
        logger.info(f"Processing PDF receipt: {pdf_path}")
        
        # Check file exists
        if not Path(pdf_path).exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return None
        
        # Extract text from PDF
        pdf_text = _extract_pdf_text(pdf_path)
        
        if not pdf_text or len(pdf_text.strip()) < 10:
            logger.error("Failed to extract text from PDF or text too short")
            return None
        
        logger.info(f"Extracted PDF text length: {len(pdf_text)} chars")
        
        # Create prompt with PDF text
        prompt = prompts.pdf_parser_prompt() + f"\n\nТЕКСТ ИЗ PDF:\n{pdf_text[:2000]}"  # Limit text length
        
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
        receipt_data = _parse_pdf_json(result_text)
        
        if not receipt_data:
            logger.error("Failed to parse PDF receipt data")
            return None
        
        # Convert to transaction format
        transaction_data = await _pdf_to_transaction(receipt_data)
        
        return transaction_data
        
    except Exception as e:
        logger.error(f"Error processing PDF receipt: {e}", exc_info=True)
        return None


def _extract_pdf_text(pdf_path: str) -> Optional[str]:
    """Extract text content from PDF"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text_parts = []
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            full_text = '\n'.join(text_parts)
            return full_text
            
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return None


def _parse_pdf_json(text: str) -> Optional[Dict]:
    """Parse JSON from PDF processing response"""
    try:
        # Remove markdown if present
        text = text.strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[1] if '\n' in text else text[3:]
        if text.endswith('```'):
            text = text.rsplit('\n', 1)[0] if '\n' in text else text[:-3]
        
        text = text.strip()
        
        data = json.loads(text)
        
        # Validate amount
        if 'amount' not in data or data['amount'] is None:
            logger.error("Missing amount in PDF data")
            return None
        
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error parsing PDF JSON: {e}")
        return None


async def _pdf_to_transaction(pdf_data: Dict) -> Optional[Dict]:
    """Convert PDF data to transaction format"""
    try:
        # Extract amount
        amount = float(pdf_data['amount'])
        if amount <= 0:
            logger.error(f"Invalid amount: {amount}")
            return None
        
        # Build description
        description_parts = []
        if pdf_data.get('merchant'):
            description_parts.append(pdf_data['merchant'])
        if pdf_data.get('description'):
            description_parts.append(pdf_data['description'])
        
        description = ' - '.join(description_parts) if description_parts else 'Покупка по PDF'
        description = description[:200]
        
        # Parse date
        date_str = pdf_data.get('date')
        if date_str:
            try:
                transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                transaction_date = datetime.now().date()
        else:
            transaction_date = datetime.now().date()
        
        # Categorize
        category = await categorize_transaction(description, amount, 'expense')
        
        # Build result
        result = {
            'type': 'expense',
            'amount': amount,
            'category_name': category['name'],
            'category_icon': category['icon'],
            'description': description,
            'date': transaction_date
        }
        
        logger.info(f"PDF converted to transaction: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error converting PDF to transaction: {e}")
        return None


async def download_document_file(bot, file_id: str, destination: str) -> bool:
    """
    Download document from Telegram
    
    Args:
        bot: Telegram bot instance
        file_id: Telegram file ID
        destination: Path where to save file
        
    Returns:
        True if successful
    """
    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, destination)
        logger.info(f"Document downloaded to {destination}")
        return True
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        return False
