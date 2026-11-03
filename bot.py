import asyncio
import logging
import os
from html import escape

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "blackstars.db")
INITIAL_CHANNEL = os.getenv("INITIAL_CHANNEL", "@websayt_yaratamz")
TARGET_REFERRALS = int(os.getenv("REWARD_REFERRALS", "100"))
REWARD_STARS = int(os.getenv("REWARD_STARS", "300"))

if not TOKEN or not ADMIN_ID:
    raise RuntimeError("BOT_TOKEN va ADMIN_ID .env faylida bo‘lishi kerak.")

logging.basicConfig(level=logging.INFO)
bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())

LANGS = ("uz", "ru", "en")
LANG_NAMES = {"uz": "🇺🇿 O‘zbekcha", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}
MENU_KEYS = ("ref_link", "referrals", "reward", "stats")
DEFAULTS = {
    "ref_link": {"uz": "🔗 Referal havolam", "ru": "🔗 Моя ссылка", "en": "🔗 My referral link"},
    "referrals": {"uz": "👥 Referallarim", "ru": "👥 Мои рефералы", "en": "👥 My referrals"},
    "reward": {"uz": "🎁 Mukofotim", "ru": "🎁 Моя награда", "en": "🎁 My reward"},
    "stats": {"uz": "📊 Statistika", "ru": "📊 Статистика", "en": "📊 Statistics"},
}
TEXT = {
    "uz": {
        "welcome": "⭐ BLACK-STARS botiga xush kelibsiz!\n\n100 ta haqiqiy referal = 300 Telegram Stars.",
        "join": "Botdan foydalanish uchun quyidagi barcha kanallarga obuna bo‘ling, keyin tekshiring.",
        "not_joined": "❌ Hali barcha kanallarga obuna bo‘lmagansiz.",
        "joined": "✅ Obuna tasdiqlandi!",
        "link": "🔗 Sizning shaxsiy referal havolangiz:\n\n{link}\n\n100 ta referal = 300 ⭐",
        "refs": "👥 Taklif qilganlaringiz: {count}\n🎯 Maqsad: {target}\n⭐ Mukofot: {stars} Stars",
        "need": "❌ Sizda {count}/{target} referal bor.\nYana {left} ta kerak.",
        "eligible": "🎉 Tabriklaymiz! Maqsadga yetdingiz. Mukofot so‘rovini yuboring.",
        "request_sent": "✅ So‘rovingiz adminga yuborildi. Admin tekshirgach Starsni qo‘lda yuboradi.",
        "already": "ℹ️ Sizda mukofot so‘rovi avval yuborilgan yoki mukofotlangan.",
        "choose_lang": "Tilni tanlang:",
        "lang_saved": "✅ Til saqlandi.",
        "admin_only": "Bu bo‘lim faqat admin uchun.",
    },
    "ru": {
        "welcome": "⭐ Добро пожаловать в BLACK-STARS!\n\n100 действительных рефералов = 300 Telegram Stars.",
        "join": "Чтобы пользоваться ботом, подпишитесь на все каналы ниже и проверьте подписку.",
        "not_joined": "❌ Вы подписались не на все каналы.",
        "joined": "✅ Подписка подтверждена!",
        "link": "🔗 Ваша реферальная ссылка:\n\n{link}\n\n100 рефералов = 300 ⭐",
        "refs": "👥 Приглашено: {count}\n🎯 Цель: {target}\n⭐ Награда: {stars} Stars",
        "need": "❌ У вас {count}/{target} рефералов.\nОсталось: {left}.",
        "eligible": "🎉 Поздравляем! Цель достигнута. Отправьте запрос на награду.",
        "request_sent": "✅ Запрос отправлен администратору. После проверки он вручную отправит Stars.",
        "already": "ℹ️ Запрос уже отправлен или награда выплачена.",
        "choose_lang": "Выберите язык:",
        "lang_saved": "✅ Язык сохранён.",
        "admin_only": "Этот раздел доступен только администратору.",
    },
    "en": {
        "welcome": "⭐ Welcome to BLACK-STARS!\n\n100 valid referrals = 300 Telegram Stars.",
        "join": "To use the bot, subscribe to all channels below, then verify.",
        "not_joined": "❌ You have not joined all required channels.",
        "joined": "✅ Subscription verified!",
        "link": "🔗 Your personal referral link:\n\n{link}\n\n100 referrals = 300 ⭐",
        "refs": "👥 Invited: {count}\n🎯 Target: {target}\n⭐ Reward: {stars} Stars",
        "need": "❌ You have {count}/{target} referrals.\nYou need {left} more.",
        "eligible": "🎉 Congratulations! Goal reached. You can request your reward.",
        "request_sent": "✅ Your request was sent to the admin. Stars will be sent manually after review.",
        "already": "ℹ️ Your reward request was already submitted or paid.",
        "choose_lang": "Choose your language:",
        "lang_saved": "✅ Language saved.",
        "admin_only": "This section is for the admin only.",
    },
}

class AddChannel(StatesGroup):
    value = State()

class EditMenu(StatesGroup):
    title = State()
    title_text = State()
    emoji = State()
    sticker = State()
    sticker_upload = State()

class Broadcast(StatesGroup):
    text = State()

async def connect():
    return await aiosqlite.connect(DB_PATH)

async def init_db():
    async with await connect() as con:
        await con.execute("""CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY, username TEXT, invited_by INTEGER,
            lang TEXT DEFAULT 'uz', joined_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        await con.execute("""CREATE TABLE IF NOT EXISTS channels(
            channel_id TEXT PRIMARY KEY, title TEXT NOT NULL, invite_link TEXT NOT NULL)""")
        await con.execute("""CREATE TABLE IF NOT EXISTS rewards(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        await con.execute("""CREATE TABLE IF NOT EXISTS menu_settings(
            menu_key TEXT PRIMARY KEY, title_uz TEXT, title_ru TEXT, title_en TEXT,
            emoji TEXT, sticker_file_id TEXT)""")
        await con.execute("""CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY, value TEXT)""")
        for key, translations in DEFAULTS.items():
            await con.execute("""INSERT OR IGNORE INTO menu_settings
                (menu_key,title_uz,title_ru,title_en,emoji,sticker_file_id)
                VALUES (?,?,?,?,?,NULL)""",
                (key, translations["uz"], translations["ru"], translations["en"], ""))
        await con.execute("INSERT OR IGNORE INTO channels(channel_id,title,invite_link) VALUES(?,?,?)",
                          (INITIAL_CHANNEL, "Websayt yaratamiz", "https://t.me/websayt_yaratamz"))
        await con.commit()

async def get_user_lang(uid):
    async with await connect() as con:
        cur = await con.execute("SELECT lang FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    return row[0] if row and row[0] in LANGS else "uz"

async def set_user_lang(uid, lang):
    if lang not in LANGS: return
    async with await connect() as con:
        await con.execute("INSERT INTO users(user_id,lang) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang",
                          (uid, lang))
        await con.commit()

async def add_user(uid, username, referrer):
    async with await connect() as con:
        cur = await con.execute("SELECT 1 FROM users WHERE user_id=?", (uid,))
        if await cur.fetchone(): return False
        if referrer == uid: referrer = None
        if referrer:
            cur = await con.execute("SELECT 1 FROM users WHERE user_id=?", (referrer,))
            if not await cur.fetchone(): referrer = None
        await con.execute("INSERT INTO users(user_id,username,invited_by,lang) VALUES(?,?,?,'uz')",
                          (uid, username, referrer))
        await con.commit()
        return True

async def user_exists(uid):
    async with await connect() as con:
        cur = await con.execute("SELECT 1 FROM users WHERE user_id=?", (uid,))
        return await cur.fetchone() is not None

async def get_count(uid):
    async with await connect() as con:
        cur = await con.execute("SELECT COUNT(*) FROM users WHERE invited_by=?", (uid,))
        return (await cur.fetchone())[0]

async def get_channels():
    async with await connect() as con:
        cur = await con.execute("SELECT channel_id,title,invite_link FROM channels ORDER BY title")
        return await cur.fetchall()

async def get_menu(key):
    async with await connect() as con:
        cur = await con.execute("SELECT title_uz,title_ru,title_en,emoji,sticker_file_id FROM menu_settings WHERE menu_key=?", (key,))
        return await cur.fetchone()

async def menu_title(key, lang):
    row = await get_menu(key)
    if not row: return DEFAULTS[key][lang]
    title = row[LANGS.index(lang)]
    emoji = row[3] or ""
    # Title may already include emoji; emoji field is optional decoration.
    return f"{emoji} {title}".strip()

async def all_menu_titles(lang):
    return {key: await menu_title(key, lang) for key in MENU_KEYS}

async def send_menu_sticker(target, key):
    row = await get_menu(key)
    if row and row[4]:
        try:
            await target.answer_sticker(row[4])
        except Exception:
            logging.exception("Menyu stikeri yuborilmadi")

async def main_keyboard(uid, lang):
    titles = await all_menu_titles(lang)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=titles["ref_link"]), KeyboardButton(text=titles["referrals"])],
            [KeyboardButton(text=titles["reward"]), KeyboardButton(text=titles["stats"])],
            [KeyboardButton(text="🌐 Til / Language")]
        ], resize_keyboard=True
    )

async def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanallar", callback_data="adm:channels"),
         InlineKeyboardButton(text="🎨 Menyu dizayni", callback_data="adm:design")],
        [InlineKeyboardButton(text="🎁 Mukofot so‘rovlari", callback_data="adm:rewards"),
         InlineKeyboardButton(text="📊 Statistika", callback_data="adm:stats")],
        [InlineKeyboardButton(text="✉️ Xabar yuborish", callback_data="adm:broadcast")],
    ])

async def check_subs(uid):
    for cid, title, link in await get_channels():
        try:
            member = await bot.get_chat_member(cid, uid)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except Exception:
            logging.exception("Subscription check failed for %s", cid)
            return False
    return True

async def sub_kb(ref=0):
    rows = []
    for cid, title, link in await get_channels():
        rows.append([InlineKeyboardButton(text=f"📢 {title}", url=link)])
    rows.append([InlineKeyboardButton(text="✅ Tekshirish / Проверить / Verify",
                                      callback_data=f"sub:{int(ref or 0)}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def require_subscription(message, ref=0):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(TEXT[lang]["join"], reply_markup=await sub_kb(ref))

async def ensure_user(message, ref=0):
    uid = message.from_user.id
    if not await check_subs(uid):
        await require_subscription(message, ref)
        return False
    await add_user(uid, message.from_user.username, ref or None)
    return True

async def bot_link(uid):
    me = await bot.get_me()
    return f"https://t.me/{me.username}?start={uid}"

async def has_open_reward(uid):
    async with await connect() as con:
        cur = await con.execute("SELECT 1 FROM rewards WHERE user_id=? AND status IN ('pending','paid')", (uid,))
        return await cur.fetchone() is not None

async def create_reward(uid):
    async with await connect() as con:
        cur = await con.execute("SELECT 1 FROM rewards WHERE user_id=? AND status IN ('pending','paid')", (uid,))
        if await cur.fetchone(): return None
        cur = await con.execute("INSERT INTO rewards(user_id,status) VALUES(?,'pending')", (uid,))
        await con.commit()
        return cur.lastrowid

@dp.message(CommandStart())
async def start(message: Message):
    ref = 0
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        try: ref = int(parts[1])
        except ValueError: pass
    uid = message.from_user.id
    if not await check_subs(uid):
        await require_subscription(message, ref)
        return
    await add_user(uid, message.from_user.username, ref or None)
    lang = await get_user_lang(uid)
    await message.answer(TEXT[lang]["welcome"], reply_markup=await main_keyboard(uid, lang))

@dp.callback_query(F.data.startswith("sub:"))
async def sub_verify(callback: CallbackQuery):
    try: ref = int(callback.data.split(":", 1)[1])
    except ValueError: ref = 0
    if not await check_subs(callback.from_user.id):
        await callback.answer(TEXT[await get_user_lang(callback.from_user.id)]["not_joined"], show_alert=True)
        return
    await add_user(callback.from_user.id, callback.from_user.username, ref or None)
    lang = await get_user_lang(callback.from_user.id)
    await callback.message.answer(TEXT[lang]["joined"], reply_markup=await main_keyboard(callback.from_user.id, lang))
    await callback.answer()

@dp.message(F.text == "🌐 Til / Language")
async def language_menu(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANG_NAMES[l], callback_data=f"lang:{l}")] for l in LANGS
    ])
    await message.answer("🌐 " + TEXT[await get_user_lang(message.from_user.id)]["choose_lang"], reply_markup=kb)

@dp.callback_query(F.data.startswith("lang:"))
async def language_set(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    if lang not in LANGS:
        await callback.answer("Invalid language", show_alert=True); return
    await set_user_lang(callback.from_user.id, lang)
    await callback.message.answer(TEXT[lang]["lang_saved"], reply_markup=await main_keyboard(callback.from_user.id, lang))
    await callback.answer()

async def user_menu_action(message, key):
    uid = message.from_user.id
    if not await check_subs(uid):
        await require_subscription(message); return
    if not await user_exists(uid):
        await add_user(uid, message.from_user.username, None)
    lang = await get_user_lang(uid)
    await send_menu_sticker(message, key)
    if key == "ref_link":
        await message.answer(TEXT[lang]["link"].format(link=await bot_link(uid)))
    elif key == "referrals":
        await message.answer(TEXT[lang]["refs"].format(count=await get_count(uid), target=TARGET_REFERRALS, stars=REWARD_STARS))
    elif key == "stats":
        count = await get_count(uid)
        await message.answer(TEXT[lang]["refs"].format(count=count, target=TARGET_REFERRALS, stars=REWARD_STARS) +
                             f"\n\n📈 {max(0, TARGET_REFERRALS-count)}")
    elif key == "reward":
        count = await get_count(uid)
        if count < TARGET_REFERRALS:
            await message.answer(TEXT[lang]["need"].format(count=count, target=TARGET_REFERRALS, left=TARGET_REFERRALS-count))
        elif await has_open_reward(uid):
            await message.answer(TEXT[lang]["already"])
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=f"🎁 {REWARD_STARS} Stars", callback_data="reward:request")
            ]])
            await message.answer(TEXT[lang]["eligible"], reply_markup=kb)

@dp.message()
async def route_menu(message: Message):
    if not message.text: return
    lang = await get_user_lang(message.from_user.id)
    for key in MENU_KEYS:
        if message.text == await menu_title(key, lang):
            await user_menu_action(message, key)
            return

@dp.callback_query(F.data == "reward:request")
async def reward_request(callback: CallbackQuery):
    uid = callback.from_user.id
    if not await check_subs(uid):
        await callback.answer("Avval barcha kanallarga obuna bo‘ling.", show_alert=True); return
    count = await get_count(uid)
    if count < TARGET_REFERRALS:
        await callback.answer("Referallar yetarli emas.", show_alert=True); return
    rid = await create_reward(uid)
    if rid is None:
        await callback.answer("So‘rov avval yuborilgan yoki to‘langan.", show_alert=True); return
    await callback.message.answer(TEXT[await get_user_lang(uid)]["request_sent"])
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ To‘landi", callback_data=f"reward:paid:{rid}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reward:reject:{rid}")
    ]])
    await bot.send_message(ADMIN_ID, f"🎁 Mukofot so‘rovi #{rid}\nUser: {uid}\nReferallar: {count}\nMukofot: {REWARD_STARS} Stars\n\nStarsni avval qo‘lda yuboring.", reply_markup=kb)
    await callback.answer("So‘rov yuborildi.")

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("⚙️ BLACK-STARS ADMIN PANEL", reply_markup=await admin_kb())

@dp.callback_query(F.data == "adm:channels")
async def channels_panel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kanal qo‘shish", callback_data="channel:add")],
        [InlineKeyboardButton(text="📋 Kanallar ro‘yxati", callback_data="channel:list")],
        [InlineKeyboardButton(text="🗑 Kanal o‘chirish", callback_data="channel:delete")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:back")]
    ])
    await callback.message.answer("📢 Kanal boshqaruvi", reply_markup=kb); await callback.answer()

@dp.callback_query(F.data == "adm:back")
async def admin_back(callback: CallbackQuery):
    if callback.from_user.id == ADMIN_ID:
        await callback.message.answer("⚙️ Admin panel", reply_markup=await admin_kb())
    await callback.answer()

@dp.callback_query(F.data == "channel:add")
async def channel_add_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    await state.set_state(AddChannel.value)
    await callback.message.answer("Kanal username yoki ID sini yuboring (masalan @kanal yoki -100...). Bot kanal administratori bo‘lishi shart.")
    await callback.answer()

@dp.message(AddChannel.value)
async def channel_add_save(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        chat = await bot.get_chat(message.text.strip())
        me = await bot.get_me()
        member = await bot.get_chat_member(chat.id, me.id)
        if member.status not in ("administrator", "creator"):
            await message.answer("❌ Avval botni kanalga administrator qiling."); return
        if chat.username:
            link = f"https://t.me/{chat.username}"
        else:
            link = (await bot.create_chat_invite_link(chat.id)).invite_link
        async with await connect() as con:
            await con.execute("INSERT INTO channels(channel_id,title,invite_link) VALUES(?,?,?)",
                              (str(chat.id), chat.title or str(chat.id), link))
            await con.commit()
        await message.answer(f"✅ Kanal qo‘shildi: {chat.title}\n{link}")
        await state.clear()
    except aiosqlite.IntegrityError:
        await message.answer("Bu kanal avval qo‘shilgan."); await state.clear()
    except Exception:
        logging.exception("Channel add error")
        await message.answer("❌ Kanal topilmadi yoki bot admin emas. Username/ID va bot huquqlarini tekshiring.")

@dp.callback_query(F.data == "channel:list")
async def channel_list(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    channels = await get_channels()
    text = "📋 Kanallar:\n\n" if channels else "Kanallar ro‘yxati bo‘sh."
    for cid, title, link in channels: text += f"• {title}\n{cid}\n{link}\n\n"
    await callback.message.answer(text); await callback.answer()

@dp.callback_query(F.data == "channel:delete")
async def channel_delete_list(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    channels = await get_channels()
    rows = [[InlineKeyboardButton(text=f"🗑 {title}", callback_data=f"channel:del:{cid}")] for cid,title,link in channels]
    if rows: await callback.message.answer("O‘chirish uchun kanalni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    else: await callback.message.answer("Kanallar yo‘q.")
    await callback.answer()

@dp.callback_query(F.data.startswith("channel:del:"))
async def channel_delete(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    cid = callback.data.split(":", 2)[2]
    async with await connect() as con:
        cur = await con.execute("DELETE FROM channels WHERE channel_id=?", (cid,))
        await con.commit()
    await callback.message.edit_text("✅ Kanal o‘chirildi." if cur.rowcount else "Kanal topilmadi.")
    await callback.answer()

@dp.callback_query(F.data == "adm:design")
async def design_panel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    rows = []
    for key in MENU_KEYS:
        title = await menu_title(key, "uz")
        rows.append([InlineKeyboardButton(text=title, callback_data=f"design:menu:{key}")])
    rows.append([InlineKeyboardButton(text="🎨 Rangli emoji mavzusi", callback_data="design:theme")])
    await callback.message.answer("🎨 Qaysi menyuni sozlaysiz?", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()

@dp.callback_query(F.data == "design:theme")
async def design_theme(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    themes = [("💜 Binafsha", "💜"), ("💙 Ko‘k", "💙"), ("💚 Yashil", "💚"), ("💛 Sariq", "💛"), ("❤️ Qizil", "❤️")]
    rows = [[InlineKeyboardButton(text=name, callback_data=f"theme:set:{emoji}")] for name,emoji in themes]
    await callback.message.answer("Mavzuni tanlang. Telegram tugmalarining fon rangi o‘zgarmaydi; bu belgi menyu matniga qo‘shiladi.", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()

@dp.callback_query(F.data.startswith("theme:set:"))
async def set_theme(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    emoji = callback.data.split(":", 2)[2]
    async with await connect() as con:
        for key in MENU_KEYS:
            await con.execute("UPDATE menu_settings SET emoji=? WHERE menu_key=?", (emoji, key))
        await con.commit()
    await callback.message.answer("✅ Menyu bezagi yangilandi. Foydalanuvchilar menyuni qayta ochganda yangi ko‘rinishni ko‘radi.")
    await callback.answer()

@dp.callback_query(F.data.startswith("design:menu:"))
async def design_menu_options(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    key = callback.data.rsplit(":", 1)[1]
    if key not in MENU_KEYS:
        await callback.answer("Noma’lum menyu", show_alert=True); return
    rows = [
        [InlineKeyboardButton(text="📝 Nomini o‘zgartirish", callback_data=f"edit:title:{key}")],
        [InlineKeyboardButton(text="😀 Emoji qo‘shish/almashtirish", callback_data=f"edit:emoji:{key}")],
        [InlineKeyboardButton(text="🖼 Stiker biriktirish", callback_data=f"edit:sticker:{key}")],
        [InlineKeyboardButton(text="🗑 Stikerni olib tashlash", callback_data=f"edit:clear:{key}")],
    ]
    await callback.message.answer("Menyu sozlamalari:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()

@dp.callback_query(F.data.startswith("edit:title:"))
async def edit_title_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    key = callback.data.rsplit(":", 1)[1]
    await state.update_data(menu_key=key)
    await state.set_state(EditMenu.title)
    await callback.message.answer("Qaysi til uchun yangi nom? uz, ru yoki en deb yuboring.")
    await callback.answer()

@dp.message(EditMenu.title)
async def edit_title_lang(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    lang = message.text.strip().lower()
    if lang not in LANGS:
        await message.answer("Faqat uz, ru yoki en yuboring."); return
    await state.update_data(lang=lang)
    await state.set_state(EditMenu.title_text)
    await message.answer(f"{LANG_NAMES[lang]} uchun yangi menyu nomini yuboring. Emoji ham qo‘shishingiz mumkin.")

# This state receives the title text; the following handler is deliberately a single step.
@dp.message(EditMenu.title_text)
async def edit_title_save(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    key, lang = data["menu_key"], data["lang"]
    if not message.text or len(message.text) > 64:
        await message.answer("Nom 1–64 belgidan iborat matn bo‘lsin."); return
    column = {"uz":"title_uz", "ru":"title_ru", "en":"title_en"}[lang]
    async with await connect() as con:
        await con.execute(f"UPDATE menu_settings SET {column}=? WHERE menu_key=?", (message.text.strip(), key))
        await con.commit()
    await message.answer("✅ Menyu nomi saqlandi.")
    await state.clear()

@dp.callback_query(F.data.startswith("edit:emoji:"))
async def edit_emoji_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    key = callback.data.rsplit(":",1)[1]
    await state.update_data(menu_key=key)
    await state.set_state(EditMenu.emoji)
    await callback.message.answer("Menyu uchun bitta emoji yuboring (masalan 💎). Olib tashlash uchun - yuboring.")
    await callback.answer()

@dp.message(EditMenu.emoji)
async def edit_emoji_save(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    emoji = "" if message.text.strip() == "-" else message.text.strip()
    if len(emoji) > 16:
        await message.answer("Iltimos, bitta emoji yuboring."); return
    async with await connect() as con:
        await con.execute("UPDATE menu_settings SET emoji=? WHERE menu_key=?", (emoji, data["menu_key"]))
        await con.commit()
    await message.answer("✅ Emoji saqlandi.")
    await state.clear()

@dp.callback_query(F.data.startswith("edit:sticker:"))
async def edit_sticker_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    key = callback.data.rsplit(":",1)[1]
    await state.update_data(menu_key=key)
    await state.set_state(EditMenu.sticker_upload)
    await callback.message.answer("Endi shu menyu uchun Telegram sticker yuboring.")
    await callback.answer()

@dp.message(EditMenu.sticker_upload, F.sticker)
async def edit_sticker_save(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    async with await connect() as con:
        await con.execute("UPDATE menu_settings SET sticker_file_id=? WHERE menu_key=?",
                          (message.sticker.file_id, data["menu_key"]))
        await con.commit()
    await message.answer("✅ Stiker menyuga biriktirildi.")
    await state.clear()

@dp.callback_query(F.data.startswith("edit:clear:"))
async def clear_sticker(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    key = callback.data.rsplit(":",1)[1]
    async with await connect() as con:
        await con.execute("UPDATE menu_settings SET sticker_file_id=NULL WHERE menu_key=?", (key,))
        await con.commit()
    await callback.answer("Stiker olib tashlandi.", show_alert=True)

@dp.callback_query(F.data == "adm:stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    async with await connect() as con:
        async def scalar(sql):
            cur = await con.execute(sql); return (await cur.fetchone())[0]
        users = await scalar("SELECT COUNT(*) FROM users")
        refs = await scalar("SELECT COUNT(*) FROM users WHERE invited_by IS NOT NULL")
        pending = await scalar("SELECT COUNT(*) FROM rewards WHERE status='pending'")
        paid = await scalar("SELECT COUNT(*) FROM rewards WHERE status='paid'")
        channels = await scalar("SELECT COUNT(*) FROM channels")
    await callback.message.answer(f"📊 STATISTIKA\n\nFoydalanuvchilar: {users}\nReferal orqali kelganlar: {refs}\nKanallar: {channels}\nKutilayotgan mukofotlar: {pending}\nTo‘langan mukofotlar: {paid}")
    await callback.answer()

@dp.callback_query(F.data == "adm:rewards")
async def admin_rewards(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    async with await connect() as con:
        cur = await con.execute("SELECT id,user_id FROM rewards WHERE status='pending' ORDER BY id")
        rows = await cur.fetchall()
    if not rows: await callback.message.answer("Kutilayotgan so‘rovlar yo‘q.")
    for rid, uid in rows:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ To‘landi", callback_data=f"reward:paid:{rid}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reward:reject:{rid}")
        ]])
        await callback.message.answer(f"So‘rov #{rid}\nUser ID: {uid}\n{REWARD_STARS} Stars", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("reward:paid:"))
async def reward_paid(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    rid = int(callback.data.rsplit(":",1)[1])
    async with await connect() as con:
        cur = await con.execute("SELECT user_id FROM rewards WHERE id=? AND status='pending'", (rid,))
        row = await cur.fetchone()
        if row:
            await con.execute("UPDATE rewards SET status='paid' WHERE id=?", (rid,))
            await con.commit()
    if row:
        try: await bot.send_message(row[0], f"🎉 {REWARD_STARS} Telegram Stars mukofotingiz admin tomonidan yuborildi.")
        except Exception: pass
        await callback.message.edit_text(callback.message.text + "\n\n✅ To‘landi deb belgilandi.")
        await callback.answer("Saqlandi.")
    else: await callback.answer("So‘rov topilmadi yoki oldin ko‘rilgan.", show_alert=True)

@dp.callback_query(F.data.startswith("reward:reject:"))
async def reward_reject(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    rid = int(callback.data.rsplit(":",1)[1])
    async with await connect() as con:
        cur = await con.execute("SELECT user_id FROM rewards WHERE id=? AND status='pending'", (rid,))
        row = await cur.fetchone()
        if row:
            await con.execute("UPDATE rewards SET status='rejected' WHERE id=?", (rid,))
            await con.commit()
    if row:
        try: await bot.send_message(row[0], "❌ Mukofot so‘rovingiz rad etildi.")
        except Exception: pass
        await callback.message.edit_text(callback.message.text + "\n\n❌ Rad etildi.")
        await callback.answer("Rad etildi.")
    else: await callback.answer("So‘rov topilmadi.", show_alert=True)

@dp.callback_query(F.data == "adm:broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo‘q", show_alert=True); return
    await state.set_state(Broadcast.text)
    await callback.message.answer("Barcha bot foydalanuvchilariga yuboriladigan matnni jo‘nating.")
    await callback.answer()

@dp.message(Broadcast.text)
async def broadcast_send(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    if not message.text:
        await message.answer("Hozircha faqat matnli xabar yuborish mumkin."); return
    async with await connect() as con:
        cur = await con.execute("SELECT user_id FROM users")
        ids = [r[0] for r in await cur.fetchall()]
    sent = 0
    for uid in ids:
        try:
            await bot.send_message(uid, message.text)
            sent += 1
        except Exception:
            pass
    await message.answer(f"Xabar yuborildi: {sent}/{len(ids)}")
    await state.clear()

async def main():
    await init_db()
    logging.info("BLACK-STARS PRO ishga tushdi.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


@dp.message(EditMenu.sticker_upload)
async def sticker_upload_invalid(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Iltimos, oddiy rasm emas, Telegram sticker yuboring.")

