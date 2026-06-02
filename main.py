import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Filter
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CHANNEL_ID = os.getenv("CHANNEL_ID")
BUTTON_TEXT = os.getenv("BUTTON_TEXT", "Записаться")
BUTTON_URL = os.getenv("BUTTON_URL", "https://t.me/masherk")
STICKER_FILE_ID = os.getenv("CAACAgIAAxkBAAFLTtNqHq513Z9PXUeZavL5P20idj_-8QACQZkAAgI68Uj2qM8I9vD_2DsE")

# Инициализируем роутер
router = Router()

# Кэш для агрегации сообщений из медиагруппы (альбома)
album_cache = {}

class IsAdmin(Filter):
    """Кастомный фильтр для проверки, что пишет администратор."""
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id == ADMIN_ID

# Вешаем фильтр на все хэндлеры роутера — бот будет реагировать только на админа
router.message.filter(IsAdmin())

def get_keyboard() -> InlineKeyboardMarkup:
    """Генерация клавиатуры с одной кнопкой-ссылкой."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=BUTTON_TEXT, url=BUTTON_URL)]]
    )

@router.message(F.media_group_id)
async def handle_album(message: Message, bot: Bot):
    """
    Хэндлер для обработки альбомов (MediaGroups).
    Собирает все части альбома и отправляет их в канал, 
    после чего добавляет отдельный стикер с кнопкой.
    """
    group_id = message.media_group_id
    
    if group_id not in album_cache:
        # Если это первое сообщение альбома, создаем список и ждем остальные части
        album_cache[group_id] = [message]
        await asyncio.sleep(2)  # Небольшой debounce
        
        # Извлекаем и удаляем альбом из кэша
        messages = album_cache.pop(group_id)
        messages.sort(key=lambda m: m.message_id)  # Сортируем по порядку отправки
        
        message_ids = [m.message_id for m in messages]
        
        try:
            # Отправляем альбом целиком в канал
            await bot.copy_messages(
                chat_id=CHANNEL_ID,
                from_chat_id=message.chat.id,
                message_ids=message_ids
            )
            # Отправляем стикер с прикрепленной кнопкой
            await bot.send_sticker(
                chat_id=CHANNEL_ID,
                sticker=STICKER_FILE_ID,
                reply_markup=get_keyboard()
            )
            await message.reply("✅ Альбом со стикером успешно отправлен в канал!")
        except Exception as e:
            logging.error(f"Ошибка при отправке альбома: {e}")
            await message.reply("❌ Ошибка при отправке альбома. Проверьте права бота и правильность STICKER_FILE_ID.")
    else:
        # Добавляем последующие элементы альбома в кэш
        album_cache[group_id].append(message)

@router.message()
async def handle_single_message(message: Message, bot: Bot):
    """
    Хэндлер для всех одиночных сообщений (текст, 1 фото, видео, кружок).
    Копирует сообщение и прикрепляет к нему inline-кнопку.
    """
    try:
        await bot.copy_message(
            chat_id=CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=get_keyboard()
        )
        await message.reply("✅ Пост успешно отправлен в канал!")
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")
        await message.reply("❌ Ошибка. Убедитесь, что бот является администратором канала.")

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Подключаем роутер к диспетчеру
    dp.include_router(router)
    
    logging.basicConfig(level=logging.INFO)
    
    # Пропускаем старые апдейты при запуске
    await bot.delete_webhook(drop_pending_updates=True)
    
    logging.info("Бот запущен и готов к работе.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
