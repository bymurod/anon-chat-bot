import asyncio
import logging
import secrets
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "YOUR_BOT_TOKEN"  # @BotFather dan oling
BOT_USERNAME = "YOUR_BOT_USERNAME"  # masalan: myanonbot (@ belgisisiz)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# {invite_token: creator_user_id}
invites = {}

# {user_id: partner_id}
pairs = {}

class ChatState(StatesGroup):
    chatting = State()

# /start — oddiy yoki invite link bilan
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, command: CommandObject):
    user_id = message.from_user.id
    arg = command.args  # /start TOKEN

    # Invite link orqali kelgan
    if arg and arg in invites:
        creator_id = invites[arg]

        if creator_id == user_id:
            await message.answer("⚠️ O'z linkingizdан kira olmaysiz.")
            return

        if user_id in pairs:
            await message.answer("⚠️ Siz allaqachon boshqa suhbatdasiz. /stop yozing.")
            return

        if creator_id not in pairs or pairs.get(creator_id) != "waiting":
            await message.answer("⚠️ Bu link allaqachon ishlatilgan yoki muddati o'tgan.")
            return

        # Ulashtirish
        del invites[arg]
        pairs[user_id] = creator_id
        pairs[creator_id] = user_id

        stop_kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🚪 Suhbatdan chiqish")]],
            resize_keyboard=True
        )

        await bot.send_message(
            creator_id,
            "✅ *Suhbatdosh ulandi!*\nAnonim suhbat boshlandi. Xabar yozing 👇\nChiqish: /stop",
            parse_mode="Markdown",
            reply_markup=stop_kb
        )
        await message.answer(
            "✅ *Ulangansiz!*\nAnonim suhbat boshlandi. Xabar yozing 👇\nChiqish: /stop",
            parse_mode="Markdown",
            reply_markup=stop_kb
        )

        await state.set_state(ChatState.chatting)

        # Creator state ni ham chatting ga o'tkazish
        creator_state = dp.fsm.get_context(bot, creator_id, creator_id)
        await creator_state.set_state(ChatState.chatting)
        return

    # Oddiy /start
    await state.clear()
    if user_id in pairs:
        del pairs[user_id]

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔗 Invite link yaratish")]],
        resize_keyboard=True
    )
    await message.answer(
        "👤 *Anonim Chat*\n\n"
        "Tanishingiz bilan anonim suhbatlashish uchun:\n"
        "1️⃣ Invite link yarating\n"
        "2️⃣ Linkni tanishingizga yuboring\n"
        "3️⃣ U link orqali kirishi bilan suhbat boshlanadi\n\n"
        "Hech kim hech kimning raqamini ko'rmaydi ✅",
        parse_mode="Markdown",
        reply_markup=kb
    )

# Invite link yaratish
@dp.message(F.text == "🔗 Invite link yaratish")
async def create_invite(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id in pairs:
        await message.answer("⚠️ Siz allaqachon suhbatdasiz. /stop yozing.")
        return

    # Eski tokenlarni tozalash (bu user uchun)
    to_delete = [k for k, v in invites.items() if v == user_id]
    for k in to_delete:
        del invites[k]

    token = secrets.token_urlsafe(12)
    invites[token] = user_id
    pairs[user_id] = "waiting"

    link = f"https://t.me/{BOT_USERNAME}?start={token}"

    cancel_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Linkni bekor qilish")]],
        resize_keyboard=True
    )

    await message.answer(
        f"🔗 *Sizning invite linkinig:*\n\n`{link}`\n\n"
        f"Yuqoridagi linkni tanishingizga yuboring.\n"
        f"U bosishi bilan suhbat avtomatik boshlanadi.\n\n"
        f"⏳ Ulanish kutilmoqda...",
        parse_mode="Markdown",
        reply_markup=cancel_kb
    )

# Linkni bekor qilish
@dp.message(F.text == "❌ Linkni bekor qilish")
async def cancel_invite(message: Message, state: FSMContext):
    user_id = message.from_user.id

    to_delete = [k for k, v in invites.items() if v == user_id]
    for k in to_delete:
        del invites[k]

    if pairs.get(user_id) == "waiting":
        del pairs[user_id]

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔗 Invite link yaratish")]],
        resize_keyboard=True
    )
    await message.answer("❌ Link bekor qilindi.", reply_markup=kb)

# Suhbatdan chiqish
@dp.message(F.text == "🚪 Suhbatdan chiqish")
@dp.message(Command("stop"))
async def stop_chat(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id in pairs and pairs[user_id] != "waiting":
        partner_id = pairs[user_id]

        del pairs[user_id]
        if partner_id in pairs:
            del pairs[partner_id]

        start_kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔗 Invite link yaratish")]],
            resize_keyboard=True
        )

        try:
            await bot.send_message(
                partner_id,
                "🚪 *Suhbatdosh chiqib ketdi.*\nYangi suhbat boshlash uchun /start bosing.",
                parse_mode="Markdown",
                reply_markup=start_kb
            )
            partner_state = dp.fsm.get_context(bot, partner_id, partner_id)
            await partner_state.clear()
        except:
            pass

        await message.answer(
            "🚪 *Suhbatdan chiqdingiz.*",
            parse_mode="Markdown",
            reply_markup=start_kb
        )
        await state.clear()
    else:
        await message.answer("Siz hozir hech qanday suhbatda emassiz. /start bosing.")

# Xabar uzatish
@dp.message(ChatState.chatting)
async def relay_message(message: Message):
    user_id = message.from_user.id

    if user_id not in pairs or pairs[user_id] == "waiting":
        await message.answer("⚠️ Suhbat topilmadi. /start bosing.")
        return

    partner_id = pairs[user_id]

    try:
        if message.text:
            await bot.send_message(partner_id, f"👤 {message.text}")
        elif message.photo:
            await bot.send_photo(partner_id, message.photo[-1].file_id)
        elif message.video:
            await bot.send_video(partner_id, message.video.file_id)
        elif message.voice:
            await bot.send_voice(partner_id, message.voice.file_id)
        elif message.sticker:
            await bot.send_sticker(partner_id, message.sticker.file_id)
        elif message.document:
            await bot.send_document(partner_id, message.document.file_id)
        elif message.video_note:
            await bot.send_video_note(partner_id, message.video_note.file_id)
        else:
            await message.answer("⚠️ Bu turdagi xabar qo'llab-quvvatlanmaydi.")
    except Exception as e:
        await message.answer("⚠️ Xabar yuborishda xatolik. Suhbatdosh uzoqlashgan bo'lishi mumkin.")
        logging.error(f"Relay error: {e}")

async def main():
    logging.basicConfig(level=logging.CRITICAL)
    print(f"Bot @{BOT_USERNAME} ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
