"""
AI Chat Handler for Telegram Bot
Handles AI assistant conversations with text, voice, photos, and PDFs
Sends ALL user transactions to AI for complete financial context
"""

import logging
import os
import tempfile
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from datetime import datetime

from telegram_bot.config import BotMessages
from telegram_bot.keyboards import ai_chat_keyboard, ai_end_keyboard
from ai.agent import chat_with_agent, reset_agent_conversation
from ai.voice_transcriber import transcribe_voice, download_voice_file
from ai.image_processor import process_receipt_image, download_photo_file
from ai.pdf_processor import process_receipt_pdf, download_document_file
from database.connection import get_db_connection
from database.repositories.transaction_repo import TransactionRepository

logger = logging.getLogger(__name__)
router = Router()


class AIChatStates(StatesGroup):
    """FSM states for AI chat"""
    in_chat = State()  # Пользователь в AI-диалоге


# ==================== HELPER FUNCTIONS ====================

async def _load_all_user_transactions(user_id: int) -> list:
    """
    Загрузить АБСОЛЮТНО ВСЕ транзакции пользователя из БД
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Список всех транзакций без ограничений
    """
    try:
        async with get_db_connection() as conn:
            transaction_repo = TransactionRepository(conn)
            
            # Получаем ВСЕ транзакции БЕЗ ЛИМИТА
            transactions = await transaction_repo.get_user_transactions(
                user_id=user_id,
                limit=5000
            )
            
            logger.info(f"Loaded ALL {len(transactions)} transactions for user {user_id}")
            
            return transactions or []
            
    except Exception as e:
        logger.error(f"Error loading user transactions: {e}", exc_info=True)
        return []


def _format_all_transactions_context(transactions: list) -> str:
    """
    Форматировать ВСЕ транзакции в полный детальный текст для AI
    БЕЗ ОГРАНИЧЕНИЙ - отправляем каждую транзакцию
    
    Args:
        transactions: Список ВСЕХ транзакций из БД
        
    Returns:
        Полный детальный текст со ВСЕМИ транзакциями
    """
    if not transactions:
        return "У пользователя пока нет транзакций."
    
    total_count = len(transactions)
    
    # Подсчитываем статистику
    total_income = 0
    total_expense = 0
    
    for t in transactions:
        if t.type == 'income':
            total_income += float(t.amount)
        else:
            total_expense += float(t.amount)
    
    balance = total_income - total_expense
    
    # Группируем по категориям
    categories_expense = {}
    categories_income = {}
    
    for t in transactions:
        amount = float(t.amount)
        category = t.category_name or "Без категории"
        
        if t.type == 'expense':
            categories_expense[category] = categories_expense.get(category, 0) + amount
        else:
            categories_income[category] = categories_income.get(category, 0) + amount
    
    # Формируем контекст
    context = f"""ПОЛНАЯ ФИНАНСОВАЯ ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:

📊 ОБЩАЯ СТАТИСТИКА:
- Всего доходов: {total_income:,.0f} ₽
- Всего расходов: {total_expense:,.0f} ₽
- Текущий баланс: {balance:,.0f} ₽
- ВСЕГО транзакций: {total_count}

💸 ВСЕ РАСХОДЫ ПО КАТЕГОРИЯМ:
"""
    
    # ВСЕ категории расходов
    sorted_expenses = sorted(categories_expense.items(), key=lambda x: x[1], reverse=True)
    for category, amount in sorted_expenses:
        count = sum(1 for t in transactions if t.type == 'expense' and (t.category_name or "Без категории") == category)
        context += f"- {category}: {amount:,.0f} ₽ ({count} транзакций)\n"
    
    context += f"\n💰 ВСЕ ДОХОДЫ ПО КАТЕГОРИЯМ:\n"
    
    # ВСЕ категории доходов
    sorted_income = sorted(categories_income.items(), key=lambda x: x[1], reverse=True)
    for category, amount in sorted_income:
        count = sum(1 for t in transactions if t.type == 'income' and (t.category_name or "Без категории") == category)
        context += f"- {category}: {amount:,.0f} ₽ ({count} транзакций)\n"
    
    # ПОЛНЫЙ СПИСОК ВСЕХ ТРАНЗАКЦИЙ
    context += f"\n📝 ПОЛНЫЙ СПИСОК ВСЕХ {total_count} ТРАНЗАКЦИЙ (от новых к старым):\n\n"
    
    for idx, t in enumerate(transactions, 1):
        date_str = t.transaction_date.strftime('%d.%m.%Y') if hasattr(t.transaction_date, 'strftime') else str(t.transaction_date)
        type_emoji = "💰" if t.type == 'income' else "💸"
        type_name = "Доход" if t.type == 'income' else "Расход"
        
        context += f"{idx}. {type_emoji} {date_str} | {type_name} | {t.category_name} | {t.amount:,.0f} ₽"
        
        if t.description:
            context += f" | {t.description}"
        
        context += "\n"
    
    context += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ВАЖНАЯ ИНФОРМАЦИЯ ДЛЯ AI:
✅ Выше представлены АБСОЛЮТНО ВСЕ {total_count} транзакций пользователя
✅ Данные полные и актуальные
✅ Используй эту информацию для:
   - Глубокого анализа финансового поведения
   - Выявления трендов и паттернов расходов
   - Персонализированных советов по оптимизации бюджета
   - Прогнозирования будущих расходов
   - Рекомендаций по экономии и инвестициям
   
💡 У тебя есть ПОЛНАЯ картина финансов пользователя - используй это для максимально точных и полезных рекомендаций!
"""
    
    return context


# ==================== AI CHAT START ====================

@router.callback_query(F.data == "ai_chat_start")
async def start_ai_chat(callback: CallbackQuery, state: FSMContext, db_user):
    """
    Start AI chat session with COMPLETE user's financial context
    Загружаем ВСЕ транзакции, отправляем полный контекст AI
    """
    await callback.answer()
    
    try:
        # Set FSM state
        await state.set_state(AIChatStates.in_chat)
        
        # Загружаем АБСОЛЮТНО ВСЕ транзакции пользователя
        logger.info(f"Loading ALL transactions for AI context: user_id={db_user.id}")
        transactions = await _load_all_user_transactions(db_user.id)
        
        # Форматируем ПОЛНЫЙ контекст со ВСЕМИ транзакциями
        context = _format_all_transactions_context(transactions)
        
        logger.info(
            f"Sending COMPLETE financial context to AI: "
            f"user_id={db_user.id}, total_transactions={len(transactions)}, "
            f"context_length={len(context)} chars"
        )
        
        # Отправляем ПОЛНЫЙ контекст AI как первое сообщение
        await chat_with_agent(
            user_id=db_user.id,
            message=context,
            new_conversation=True  # Начинаем новую сессию с полным контекстом
        )
        
        # Send welcome message to user
        await callback.message.answer(
            BotMessages.AI_WELCOME,
            reply_markup=ai_end_keyboard()
        )
        
        logger.info(f"AI chat started with FULL context for user {db_user.id}")
        
    except Exception as e:
        logger.error(f"Error starting AI chat: {e}", exc_info=True)
        await callback.message.answer(
            "❌ Ошибка при запуске AI помощника. Попробуйте позже.",
            reply_markup=ai_chat_keyboard()
        )


# ==================== TEXT MESSAGE HANDLER ====================

@router.message(AIChatStates.in_chat, F.text & ~F.text.startswith('/'))
async def handle_ai_text(message: Message, state: FSMContext, db_user):
    """
    Handle text messages in AI chat mode
    Отправляем текст пользователя AI и получаем ответ
    """
    try:
        # Show typing indicator
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        user_message = message.text
        logger.info(f"AI text from user {db_user.id}: {user_message[:100]}")
        
        # Get AI response (new_conversation=False - продолжаем сессию)
        ai_response = await chat_with_agent(
            user_id=db_user.id,
            message=user_message,
            new_conversation=False
        )
        
        if ai_response:
            # Send AI response with "End dialog" button
            await message.answer(
                ai_response,
                reply_markup=ai_end_keyboard()
            )
            logger.info(f"AI response sent to user {db_user.id}")
        else:
            await message.answer(
                BotMessages.AI_ERROR,
                reply_markup=ai_end_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error in AI text handler: {e}", exc_info=True)
        await message.answer(
            BotMessages.AI_ERROR,
            reply_markup=ai_end_keyboard()
        )


# ==================== VOICE MESSAGE HANDLER ====================

@router.message(AIChatStates.in_chat, F.voice)
async def handle_ai_voice(message: Message, state: FSMContext, db_user):
    """
    Handle voice messages in AI chat mode
    Транскрибируем голос, отправляем AI, получаем ответ
    """
    processing_msg = await message.answer("🎤 Обрабатываю голосовое сообщение...")
    
    temp_file = None
    temp_path = None
    
    try:
        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.ogg',
            delete=False,
            dir='/tmp'
        )
        temp_path = temp_file.name
        temp_file.close()
        
        # Download voice file
        success = await download_voice_file(
            bot=message.bot,
            file_id=message.voice.file_id,
            destination=temp_path
        )
        
        if not success:
            await processing_msg.edit_text("❌ Ошибка загрузки голосового сообщения")
            return
        
        # Transcribe voice
        from openai import AsyncOpenAI
        from ai.config import ai_config
        
        # Transcribe with Whisper
        async with AsyncOpenAI(api_key=ai_config.OPENAI_API_KEY) as client:
            with open(temp_path, 'rb') as audio_file:
                transcript = await client.audio.transcriptions.create(
                    model=ai_config.WHISPER_MODEL,
                    file=audio_file,
                    language="ru"
                )
        
        transcribed_text = transcript.text
        logger.info(f"AI voice transcribed for user {db_user.id}: {transcribed_text}")
        
        if not transcribed_text or len(transcribed_text.strip()) < 3:
            await processing_msg.edit_text("❌ Не удалось распознать речь")
            return
        
        # Show user's transcribed message
        await processing_msg.edit_text(f"🎤 Вы сказали: {transcribed_text}")
        
        # Show typing
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # Get AI response
        ai_response = await chat_with_agent(
            user_id=db_user.id,
            message=transcribed_text,
            new_conversation=False
        )
        
        if ai_response:
            await message.answer(
                ai_response,
                reply_markup=ai_end_keyboard()
            )
        else:
            await message.answer(
                BotMessages.AI_ERROR,
                reply_markup=ai_end_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error in AI voice handler: {e}", exc_info=True)
        await processing_msg.edit_text(BotMessages.AI_ERROR)
    
    finally:
        # Cleanup temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.error(f"Error deleting temp file: {e}")


# ==================== PHOTO HANDLER ====================

@router.message(AIChatStates.in_chat, F.photo)
async def handle_ai_photo(message: Message, state: FSMContext, db_user):
    """
    Handle photo in AI chat mode
    Распознаем чек, анализируем через AI
    """
    processing_msg = await message.answer("📸 Обрабатываю фото...")
    
    temp_file = None
    temp_path = None
    
    try:
        # Get largest photo
        photo = message.photo[-1]
        
        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.jpg',
            delete=False,
            dir='/tmp'
        )
        temp_path = temp_file.name
        temp_file.close()
        
        # Download photo
        success = await download_photo_file(
            bot=message.bot,
            file_id=photo.file_id,
            destination=temp_path
        )
        
        if not success:
            await processing_msg.edit_text("❌ Ошибка загрузки фото")
            return
        
        # Process receipt
        receipt_data = await process_receipt_image(temp_path)
        
        if not receipt_data:
            await processing_msg.edit_text(
                "❌ Не удалось распознать чек на фото.\n\n"
                "Попробуйте сделать фото более чётко."
            )
            return
        
        # Format receipt info for AI
        receipt_text = (
            f"Пользователь прислал чек:\n"
            f"Сумма: {receipt_data['amount']} ₽\n"
            f"Описание: {receipt_data['description']}\n"
            f"Категория: {receipt_data['category_name']}\n\n"
            f"Проанализируй эту покупку и дай рекомендации."
        )
        
        # Show receipt info
        await processing_msg.edit_text(
            f"📸 Распознанный чек:\n\n"
            f"💰 Сумма: {receipt_data['amount']} ₽\n"
            f"📝 {receipt_data['description']}\n"
            f"📁 {receipt_data['category_icon']} {receipt_data['category_name']}"
        )
        
        # Show typing
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # Get AI analysis
        ai_response = await chat_with_agent(
            user_id=db_user.id,
            message=receipt_text,
            new_conversation=False
        )
        
        if ai_response:
            await message.answer(
                ai_response,
                reply_markup=ai_end_keyboard()
            )
        else:
            await message.answer(
                BotMessages.AI_ERROR,
                reply_markup=ai_end_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error in AI photo handler: {e}", exc_info=True)
        await processing_msg.edit_text(BotMessages.AI_ERROR)
    
    finally:
        # Cleanup
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.error(f"Error deleting temp file: {e}")


# ==================== DOCUMENT (PDF) HANDLER ====================

@router.message(AIChatStates.in_chat, F.document)
async def handle_ai_document(message: Message, state: FSMContext, db_user):
    """
    Handle PDF documents in AI chat mode
    Парсим PDF чек, анализируем через AI
    """
    # Check if PDF
    if not message.document.file_name.lower().endswith('.pdf'):
        await message.answer(
            "❌ Поддерживаются только PDF файлы.\n"
            "Для AI-анализа отправьте PDF чек или напишите текстом.",
            reply_markup=ai_end_keyboard()
        )
        return
    
    processing_msg = await message.answer("📄 Обрабатываю PDF...")
    
    temp_file = None
    temp_path = None
    
    try:
        # Check file size
        if message.document.file_size > 20 * 1024 * 1024:
            await processing_msg.edit_text("❌ Файл слишком большой (максимум 20MB)")
            return
        
        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.pdf',
            delete=False,
            dir='/tmp'
        )
        temp_path = temp_file.name
        temp_file.close()
        
        # Download PDF
        success = await download_document_file(
            bot=message.bot,
            file_id=message.document.file_id,
            destination=temp_path
        )
        
        if not success:
            await processing_msg.edit_text("❌ Ошибка загрузки PDF")
            return
        
        # Process PDF receipt
        receipt_data = await process_receipt_pdf(temp_path)
        
        if not receipt_data:
            await processing_msg.edit_text(
                "❌ Не удалось распознать чек в PDF.\n\n"
                "Убедитесь что PDF содержит текст."
            )
            return
        
        # Format receipt info for AI
        receipt_text = (
            f"Пользователь прислал PDF чек:\n"
            f"Сумма: {receipt_data['amount']} ₽\n"
            f"Описание: {receipt_data['description']}\n"
            f"Категория: {receipt_data['category_name']}\n\n"
            f"Проанализируй эту покупку и дай рекомендации."
        )
        
        # Show receipt info
        await processing_msg.edit_text(
            f"📄 Распознанный PDF чек:\n\n"
            f"💰 Сумма: {receipt_data['amount']} ₽\n"
            f"📝 {receipt_data['description']}\n"
            f"📁 {receipt_data['category_icon']} {receipt_data['category_name']}"
        )
        
        # Show typing
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # Get AI analysis
        ai_response = await chat_with_agent(
            user_id=db_user.id,
            message=receipt_text,
            new_conversation=False
        )
        
        if ai_response:
            await message.answer(
                ai_response,
                reply_markup=ai_end_keyboard()
            )
        else:
            await message.answer(
                BotMessages.AI_ERROR,
                reply_markup=ai_end_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error in AI document handler: {e}", exc_info=True)
        await processing_msg.edit_text(BotMessages.AI_ERROR)
    
    finally:
        # Cleanup
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.error(f"Error deleting temp file: {e}")


# ==================== END AI CHAT ====================

@router.callback_query(F.data == "ai_chat_end")
async def end_ai_chat(callback: CallbackQuery, state: FSMContext, db_user):
    """
    End AI chat session and return to main menu
    Завершаем AI-диалог, сбрасываем состояние, показываем главное меню с кнопкой
    """
    await callback.answer()
    
    # Clear FSM state
    await state.clear()
    
    # Reset AI conversation
    await reset_agent_conversation(db_user.id)
    
    # Send start message WITH AI BUTTON
    await callback.message.answer(
        BotMessages.WELCOME,
        reply_markup=ai_chat_keyboard()  # ✅ КНОПКА AI ПОМОЩНИК
    )
    
    logger.info(f"AI chat ended for user {db_user.id}")


# ==================== HANDLE /start IN AI CHAT ====================

@router.message(AIChatStates.in_chat, Command("start"))
async def ai_chat_start_command(message: Message, state: FSMContext, db_user):
    """
    Handle /start command while in AI chat
    Завершаем AI-диалог и показываем главное меню с кнопкой
    """
    # Clear FSM state
    await state.clear()
    
    # Reset AI conversation
    await reset_agent_conversation(db_user.id)
    
    # Send start message WITH AI BUTTON
    await message.answer(
        BotMessages.WELCOME,
        reply_markup=ai_chat_keyboard()  # ✅ КНОПКА AI ПОМОЩНИК
    )
    
    logger.info(f"AI chat ended via /start for user {db_user.id}")
