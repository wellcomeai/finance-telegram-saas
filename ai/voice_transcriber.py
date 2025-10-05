"""
Voice transcription using OpenAI Whisper
"""

import logging
from typing import List, Dict
from openai import AsyncOpenAI
from pathlib import Path

from ai.config import ai_config
from ai.text_parser import parse_transaction_text

logger = logging.getLogger(__name__)


async def transcribe_voice(audio_file_path: str) -> List[Dict]:
    """
    Transcribe voice message and parse transaction(s)
    
    Args:
        audio_file_path: Path to audio file (.ogg, .mp3, etc.)
        
    Returns:
        List of transaction data dictionaries (может быть пустым списком)
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
    try:
        logger.info(f"Transcribing voice message: {audio_file_path}")
        
        # Check file exists
        file_path = Path(audio_file_path)
        if not file_path.exists():
            logger.error(f"Audio file not found: {audio_file_path}")
            return []
        
        # Check file size (optional safety check)
        file_size = file_path.stat().st_size
        if file_size > 25 * 1024 * 1024:  # 25MB limit
            logger.error(f"Audio file too large: {file_size} bytes")
            return []
        
        logger.info(f"Audio file size: {file_size} bytes")
        
        # Transcribe with Whisper
        async with AsyncOpenAI(api_key=ai_config.OPENAI_API_KEY) as client:
            with open(audio_file_path, 'rb') as audio_file:
                transcript = await client.audio.transcriptions.create(
                    model=ai_config.WHISPER_MODEL,
                    file=audio_file,
                    language="ru"  # Russian language
                )
        
        transcribed_text = transcript.text
        logger.info(f"Transcribed text: {transcribed_text}")
        
        if not transcribed_text or len(transcribed_text.strip()) < 3:
            logger.warning("Transcribed text too short")
            return []
        
        # Parse transaction(s) from transcribed text - теперь возвращает список
        transactions = await parse_transaction_text(transcribed_text)
        
        if transactions and len(transactions) > 0:
            logger.info(
                f"Successfully parsed {len(transactions)} transaction(s) from voice: "
                f"{[f\"{t['type']} {t['amount']} ₽\" for t in transactions]}"
            )
        else:
            logger.warning("Failed to parse transactions from transcribed text")
        
        return transactions
        
    except Exception as e:
        logger.error(f"Error transcribing voice: {e}", exc_info=True)
        return []


async def download_voice_file(bot, file_id: str, destination: str) -> bool:
    """
    Download voice file from Telegram
    
    Args:
        bot: Telegram bot instance
        file_id: Telegram file ID
        destination: Path where to save file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get file info first
        file = await bot.get_file(file_id)
        logger.info(f"Downloading voice file: {file.file_path}, size: {file.file_size} bytes")
        
        # Download file
        await bot.download_file(file.file_path, destination)
        logger.info(f"Voice file downloaded to {destination}")
        return True
        
    except Exception as e:
        logger.error(f"Error downloading voice file: {e}", exc_info=True)
        return False
