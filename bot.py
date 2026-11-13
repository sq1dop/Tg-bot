import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, LabeledPrice, PreCheckoutQuery, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# --- НАСТРОЙКИ ---
# Токен берётся из переменной окружения (Railway → Variables)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Канал для проверки подписки (обязательный)
CHECK_CHANNEL_ID = -1004376383753

# Приватный канал, куда выдаём доступ после оплаты
PAID_CHANNEL_ID = -1003947566657

# Ссылка на обязательный канал (для кнопки "Подписаться")
CHECK_CHANNEL_LINK = "https://t.me/твой_обязательный_канал"

# Цена в звёздах
PRICE = 250

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- ПРОВЕРКА ПОДПИСКИ ---
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHECK_CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
        return False

# --- КЛАВИАТУРА ПОДПИСКИ ---
def get_subscribe_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHECK_CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
    ])

# --- СТАРТ ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    if await is_subscribed(user_id):
        await send_offer(message)
    else:
        await message.answer(
            "👋 <b>Йо, брат!</b>\n\n"
            "Чтобы получить доступ к закрытому каналу, сначала подпишись на наш паблик.\n\n"
            "Жми кнопку ниже, а потом возвращайся и жми «Я подписался» 👇",
            reply_markup=get_subscribe_keyboard()
        )

# --- КНОПКА "Я ПОДПИСАЛСЯ" ---
@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(call: CallbackQuery):
    user_id = call.from_user.id
    if await is_subscribed(user_id):
        await call.message.delete()
        await send_offer(call.message)
    else:
        await call.answer("Ты ещё не подписался! 😤", show_alert=True)

# --- ОТПРАВКА СЧЁТА ---
async def send_offer(message: Message):
    offer_text = (
        "🔥 <b>Отлично, доступ разрешён!</b>\n\n"
        "Теперь осталось оплатить вход в закрытый канал.\n"
        f"Цена вопроса: <b>{PRICE} звёзд</b> ⭐\n\n"
        "Жми кнопку ниже и залетай 👇"
    )
    await message.answer_invoice(
        title="Вход в закрытый канал",
        description=f"Одноразовая ссылка на вступление. Цена: {PRICE} Stars.",
        payload="channel_access_250",
        currency="XTR",
        prices=[LabeledPrice(label="Доступ в канал", amount=PRICE)],
    )

# --- ПОДТВЕРЖДЕНИЕ ОПЛАТЫ ---
@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

# --- ВЫДАЧА ССЫЛКИ ---
@dp.message(F.successful_payment)
async def on_payment_success(message: Message):
    if message.successful_payment.invoice_payload != "channel_access_250":
        return

    try:
        invite_link = await bot.create_chat_invite_link(
            chat_id=PAID_CHANNEL_ID,
            member_limit=1,
            name=f"Access for {message.from_user.id}"
        )
        success_text = (
            "🔥 <b>Оплата прошла, брат!</b>\n\n"
            "Держи свою заветную ссылку. Она <b>одноразовая</b> — "
            "как только зайдёшь, она сгорит. Никому не пересылай!\n\n"
            f"👉 {invite_link.invite_link}\n\n"
            "Добро пожаловать в клуб 😎"
        )
        await message.answer(success_text)
    except Exception as e:
        logging.error(f"Ошибка при создании ссылки: {e}")
        await message.answer("Оплата прошла, но я не смог создать ссылку. Напиши админу.")

# --- ЗАПУСК ---
async def main():
    await dp.start_polling(bot)

# --- ВРЕМЕННАЯ КОМАНДА ДЛЯ ТЕСТА (УДАЛИТЬ ПОСЛЕ ПРОВЕРКИ!) ---
@dp.message(Command("fake_pay"))
async def fake_payment(message: Message):
    # Имитируем структуру успешного платежа
    fake_payment_data = type('obj', (object,), {
        'invoice_payload': 'channel_access_250'
    })
    
    fake_message = message.model_copy(update={
        'successful_payment': fake_payment_data
    })
    
    # Вызываем нашу функцию выдачи
    await on_payment_success(fake_message)
# -------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())
