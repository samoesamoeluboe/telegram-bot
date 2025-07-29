import os
import json
import logging
from dotenv import load_dotenv
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler
)

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка конфигурации
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_CHAT_ID = 6787660091  # Ваш chat_id

with open('responses.json', 'r', encoding='utf-8') as f:
    RESPONSES = json.load(f)

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start"""
    menu = RESPONSES["main_menu"]
    keyboard = [
        [button] for row in menu["reply_markup"]["keyboard"]
        for button in row
    ]
    await update.message.reply_text(
        text=menu["text"],
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False
        )
    )

async def send_curator_text(update: Update, context: CallbackContext) -> None:
    """Отправка кураторского текста"""
    await update.message.reply_text(
        text=RESPONSES["curator_text"]["text"],
        reply_markup=ReplyKeyboardMarkup(
            [[btn] for row in RESPONSES["main_menu"]["reply_markup"]["keyboard"] for btn in row],
            resize_keyboard=True
        )
    )

async def send_video_menu(update: Update, context: CallbackContext) -> None:
    """Меню с видео"""
    menu = RESPONSES["video_menu"]
    buttons = [
        [InlineKeyboardButton(btn["text"], callback_data=btn["callback_data"])]
        for row in menu["reply_markup"]["inline_keyboard"]
        for btn in row
    ]
    
    await update.message.reply_text(
        text=menu["text"],
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_video_choice(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    try:
        video_data = RESPONSES["videos"][query.data]
        file_id = video_data["video_url"]
        
        caption = (
            f"<b>{video_data['title']}</b>\n\n"
            f"{video_data['description']}\n\n"
            f"<i>Характеристики:</i>\n"
            f"{video_data['specs']}"
        )
        
        await context.bot.send_video(
            chat_id=query.message.chat_id,
            video=file_id,
            caption=caption,
            parse_mode="HTML"
        )
        
    except KeyError:
        logger.error(f"Видео {query.data} не найдено в конфигурации")
        await query.message.reply_text("⚠️ Это видео временно недоступно.")
    except Exception as e:
        logger.error(f"Ошибка при отправке видео: {e}")
        await query.message.reply_text("⚠️ Не удалось загрузить видео. Пожалуйста, попробуйте позже.")
    
    await send_video_menu_after_video(query.message.chat_id, context)

async def send_video_menu_after_video(chat_id: int, context: CallbackContext) -> None:
    """Отправка меню видео после показа видео"""
    menu = RESPONSES["video_menu"]
    buttons = [
        [InlineKeyboardButton(btn["text"], callback_data=btn["callback_data"])]
        for row in menu["reply_markup"]["inline_keyboard"]
        for btn in row
    ]
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="Выберите следующее видео:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_video_upload(update: Update, context: CallbackContext) -> None:
    """Обработчик загрузки видео для получения file_id"""
    try:
        if update.message.from_user.id != ADMIN_CHAT_ID:
            await update.message.reply_text("🚫 Доступ запрещен")
            return
            
        video = update.message.video
        file_id = video.file_id
        
        # Сохраняем file_id в файл
        with open("video_ids.txt", "a", encoding="utf-8") as f:
            f.write(f"{video.file_name or 'no_name'}: {file_id}\n")
        
        await update.message.reply_text(
            f"✅ Видео получено!\n"
            f"├ Имя: {video.file_name or 'Без названия'}\n"
            f"├ ID: <code>{file_id}</code>\n"
            f"└ Размер: {video.file_size//1024} KB",
            parse_mode="HTML"
        )
        
        # Пересылаем видео администратору для проверки
        await context.bot.forward_message(
            chat_id=ADMIN_CHAT_ID,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке видео: {e}")
        await update.message.reply_text("🚨 Произошла ошибка при обработке видео")

def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & filters.Text("📜 кураторский_текст"), send_curator_text))
    application.add_handler(MessageHandler(filters.TEXT & filters.Text("🎬 экспозиционные_видеоматериалы"), send_video_menu))
    application.add_handler(CallbackQueryHandler(handle_video_choice))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video_upload))
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
