"""
🌟 World Cup 2026 Charity Prediction Bot
نسخه ۲.۰ - مقاوم در برابر کرش
"""

import os
import sys
import asyncio
import logging
import sqlite3
import traceback
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
)
from dotenv import load_dotenv

# ============================================
# ⚙️ تنظیمات لاگینگ (برای دیدن خطاها)
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# ⚙️ بارگذاری متغیرهای محیطی
# ============================================
try:
    load_dotenv()
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
    SOLANA_WALLET = os.getenv('SOLANA_PLATFORM_WALLET', '')
    REQUIRED_SOL = float(os.getenv('DONATION_AMOUNT_SOL', '0.035'))
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN در فایل .env یافت نشد!")
        sys.exit(1)
    
    logger.info("✅ متغیرهای محیطی با موفقیت بارگذاری شدند")
except Exception as e:
    logger.error(f"❌ خطا در بارگذاری متغیرهای محیطی: {e}")
    sys.exit(1)

# ============================================
# 🗄️ دیتابیس SQLite با مدیریت خطا
# ============================================
DB_FILE = 'bot_database.db'

def init_db():
    """ساخت دیتابیس با مدیریت خطا"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # جدول کاربران
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        tg_id INTEGER PRIMARY KEY,
                        username TEXT,
                        lang TEXT,
                        country TEXT,
                        email TEXT,
                        wallet TEXT,
                        memo_code TEXT,
                        status TEXT DEFAULT 'pending',
                        prediction_champion TEXT,
                        prediction_runner TEXT,
                        prediction_third TEXT,
                        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')
        
        # جدول تورنمنت‌ها
        c.execute('''CREATE TABLE IF NOT EXISTS tournaments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        sport TEXT,
                        teams TEXT,
                        status TEXT DEFAULT 'active'
                    )''')
        
        conn.commit()
        conn.close()
        logger.info("✅ دیتابیس با موفقیت ساخته شد")
        return True
    except Exception as e:
        logger.error(f"❌ خطا در ساخت دیتابیس: {e}")
        logger.error(traceback.format_exc())
        return False

# ============================================
# 🌐 زبان‌ها و کشورها
# ============================================
LANGUAGES = {
    "fa": "🇮🇷 فارسی", "en": "🇬🇧 English", "de": "🇩🇪 Deutsch",
    "fr": "🇫🇷 Français", "es": "🇪🇸 Español", "ar": "🇸🇦 العربية",
    "tr": "🇹🇷 Türkçe", "ru": "🇷🇺 Русский", "zh": "🇨🇳 中文",
    "ja": "🇯🇵 日本語", "ko": "🇰🇷 한국어", "hi": "🇮🇳 हिन्दी",
    "ur": "🇵🇰 اردو", "hy": "🇦🇲 Հայերեն", "he": "🇮🇱 עברית"
}

COUNTRIES = [
    "Iran", "Germany", "France", "USA", "Brazil", "Argentina",
    "Spain", "England", "Japan", "South Korea", "Saudi Arabia",
    "Turkey", "UAE", "Canada", "Australia", "Morocco", "Other"
]

# ============================================
# 📝 متن‌های چندزبانه
# ============================================
TEXTS = {
    "fa": {
        "welcome": """
🌟 به بزرگترین پلتفرم پیش‌بینی ورزشی با هدف خیریه خوش آمدید! 🌟

🔹 این پلتفرم هیچ‌گونه ماهیت قمار (Gambling) ندارد و صرفاً یک "مسابقه پیش‌بینی ورزشی با ورودی خیریه (Donation)" است.
🔹 تمام ۷۵٪ از دونیت‌ها مستقیماً به یونیسف (UNICEF) و اتحادیه بین‌المللی کنترل سرطان (UICC) اهدا می‌شود.
🔹 شفافیت مطلق با تکنولوژی Provably Fair.

🏆 قوانین جوایز (۲۰٪ کل دونیت‌ها):
1️⃣ پیش‌بینی کامل (۳ تیم): ۲۰۲۶ برنده (هر نفر ۰.۰۰۳٪)
2️⃣ پیش‌بینی دو تیم: ۲۰۲۶ برنده (هر نفر ۰.۰۰۲٪)
3️⃣ پیش‌بینی یک تیم: ۲۰۲۶ برنده (هر نفر ۰.۰۰۱٪)
4️⃣ قرعه‌کشی شانس: ۴۶۵۹۸ برنده (هر نفر ۰.۰۰۰۱۶۸٪)

💵 هزینه دونیت: معادل ۵ دلار (حدود ۰.۰۳۵ سولانا)
""",
        "select_lang": "🌍 زبان خود را انتخاب کنید:",
        "select_country": "🌍 کشور خود را انتخاب کنید:",
        "enter_email": "📧 لطفاً ایمیل خود را وارد کنید:",
        "enter_wallet": "💼 لطفاً آدرس ولت سولانا خود را وارد کنید:",
        "payment_info": """
💎 مرحله پرداخت دونیت

لطفاً مبلغ {amount} SOL را به آدرس زیر واریز کنید:
`{wallet}`

🚨 بسیار مهم: در قسمت **Memo / Note** تراکنش، حتماً کد زیر را وارد کنید:
`{memo}`

پس از واریز، دکمه زیر را بزنید.
""",
        "payment_success": "✅ پرداخت شما تایید شد! اکنون می‌توانید پیش‌بینی خود را ثبت کنید.",
        "payment_failed": "❌ تراکنش یافت نشد. لطفاً چند دقیقه صبر کنید یا با پشتیبانی تماس بگیرید.",
        "predict_champion": "🏆 تیم قهرمان را انتخاب کنید:",
        "predict_runner": "🥈 تیم نایب قهرمان را انتخاب کنید:",
        "predict_third": "🥉 تیم سوم را انتخاب کنید:",
        "prediction_saved": "✅ پیش‌بینی شما با موفقیت ثبت شد! منتظر قرعه‌کشی نهایی باشید.",
        "support": "💬 سوال خود را بنویسید تا به پشتیبانی ارسال شود:"
    },
    "en": {
        "welcome": "Welcome! (English version - same rules as Persian)",
        "select_lang": "🌍 Select your language:",
        "select_country": "🌍 Select your country:",
        "enter_email": "📧 Please enter your email:",
        "enter_wallet": "💼 Please enter your Solana wallet address:",
        "payment_info": "💎 Donation: Send {amount} SOL to `{wallet}` with Memo: `{memo}`",
        "payment_success": "✅ Payment confirmed! Now make your predictions.",
        "payment_failed": "❌ Transaction not found. Please wait or contact support.",
        "predict_champion": "🏆 Select Champion:",
        "predict_runner": "🥈 Select Runner-up:",
        "predict_third": "🥉 Select Third place:",
        "prediction_saved": "✅ Prediction saved! Wait for the final draw.",
        "support": "💬 Write your question for support:"
    }
}

# ============================================
# 🔄 Stateها
# ============================================
class RegStates(StatesGroup):
    lang = State()
    country = State()
    email = State()
    wallet = State()
    payment = State()
    predict_champion = State()
    predict_runner = State()
    predict_third = State()
    support = State()

# ============================================
# 🚀 هندلرهای ربات با Error Handling
# ============================================

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    try:
        buttons = []
        row = []
        for code, name in LANGUAGES.items():
            row.append(InlineKeyboardButton(text=name, callback_data=f"lang_{code}"))
            if len(row) == 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(TEXTS["en"]["select_lang"], reply_markup=kb)
        await state.set_state(RegStates.lang)
    except Exception as e:
        logger.error(f"خطا در cmd_start: {e}")
        logger.error(traceback.format_exc())
        await message.answer("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")

@dp.callback_query(F.data.startswith('lang_'))
async def process_lang(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = callback.data.split('_')[1]
        await state.update_data(lang=lang, tg_id=callback.from_user.id, username=callback.from_user.username or "")
        
        welcome_text = TEXTS.get(lang, TEXTS["en"])["welcome"]
        await callback.message.edit_text(welcome_text)
        
        buttons = []
        row = []
        for country in COUNTRIES:
            row.append(InlineKeyboardButton(text=country, callback_data=f"country_{country}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.answer(TEXTS[lang]["select_country"], reply_markup=kb)
        await state.set_state(RegStates.country)
        await callback.answer()
    except Exception as e:
        logger.error(f"خطا در process_lang: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)

@dp.callback_query(F.data.startswith('country_'))
async def process_country(callback: types.CallbackQuery, state: FSMContext):
    try:
        country = callback.data.split('_')[1]
        await state.update_data(country=country)
        data = await state.get_data()
        lang = data.get('lang', 'en')
        
        await callback.message.edit_text(TEXTS[lang]["enter_email"])
        await state.set_state(RegStates.email)
        await callback.answer()
    except Exception as e:
        logger.error(f"خطا در process_country: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)

@dp.message(RegStates.email)
async def process_email(message: types.Message, state: FSMContext):
    try:
        await state.update_data(email=message.text)
        data = await state.get_data()
        lang = data.get('lang', 'en')
        await message.answer(TEXTS[lang]["enter_wallet"])
        await state.set_state(RegStates.wallet)
    except Exception as e:
        logger.error(f"خطا در process_email: {e}")
        await message.answer("❌ خطایی رخ داد")

@dp.message(RegStates.wallet)
async def process_wallet(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        lang = data.get('lang', 'en')
        
        memo_code = f"P{data['tg_id']}"
        await state.update_data(wallet=message.text, memo_code=memo_code)
        
        payment_text = TEXTS[lang]["payment_info"].format(
            amount=REQUIRED_SOL,
            wallet=SOLANA_WALLET,
            memo=memo_code
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ پرداخت انجام شد / I have paid", callback_data="check_payment")]
        ])
        await message.answer(payment_text, parse_mode="Markdown", reply_markup=kb)
        await state.set_state(RegStates.payment)
    except Exception as e:
        logger.error(f"خطا در process_wallet: {e}")
        await message.answer("❌ خطایی رخ داد")

@dp.callback_query(F.data == 'check_payment')
async def check_payment(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        lang = data.get('lang', 'en')
        
        # ذخیره در دیتابیس
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO users 
                     (tg_id, username, lang, country, email, wallet, memo_code, status)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (data['tg_id'], data['username'], data['lang'], data['country'],
                   data['email'], data['wallet'], data['memo_code'], 'paid'))
        conn.commit()
        conn.close()
        
        await callback.message.edit_text(TEXTS[lang]["payment_success"])
        logger.info(f"✅ کاربر {data['tg_id']} با موفقیت ثبت‌نام کرد")
        
        # شروع پیش‌بینی
        await show_teams_selection(callback.message, state, "champion")
        await callback.answer()
    except Exception as e:
        logger.error(f"خطا در check_payment: {e}")
        logger.error(traceback.format_exc())
        await callback.answer("❌ خطایی رخ داد", show_alert=True)

async def show_teams_selection(message, state: FSMContext, step: str):
    try:
        data = await state.get_data()
        lang = data.get('lang', 'en')
        
        teams = [
            "USA", "Canada", "Mexico", "Argentina", "Brazil", "France",
            "Germany", "Spain", "England", "Portugal", "Netherlands",
            "Belgium", "Italy", "Croatia", "Morocco", "Japan", "South Korea",
            "Saudi Arabia", "Iran", "Australia"
        ]
        
        buttons = []
        row = []
        for team in teams:
            row.append(InlineKeyboardButton(text=team, callback_data=f"team_{step}_{team}"))
            if len(row) == 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        if step == "champion":
            text = TEXTS[lang]["predict_champion"]
            await state.set_state(RegStates.predict_champion)
        elif step == "runner":
            text = TEXTS[lang]["predict_runner"]
            await state.set_state(RegStates.predict_runner)
        elif step == "third":
            text = TEXTS[lang]["predict_third"]
            await state.set_state(RegStates.predict_third)
        
        await message.answer(text, reply_markup=kb)
    except Exception as e:
        logger.error(f"خطا در show_teams_selection: {e}")

@dp.callback_query(F.data.startswith('team_'))
async def process_team(callback: types.CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split('_')
        step = parts[1]
        team = parts[2]
        
        data = await state.get_data()
        tg_id = data['tg_id']
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        if step == "champion":
            c.execute("UPDATE users SET prediction_champion=? WHERE tg_id=?", (team, tg_id))
            conn.commit()
            conn.close()
            await show_teams_selection(callback.message, state, "runner")
        elif step == "runner":
            c.execute("UPDATE users SET prediction_runner=? WHERE tg_id=?", (team, tg_id))
            conn.commit()
            conn.close()
            await show_teams_selection(callback.message, state, "third")
        elif step == "third":
            c.execute("UPDATE users SET prediction_third=? WHERE tg_id=?", (team, tg_id))
            conn.commit()
            conn.close()
            lang = data.get('lang', 'en')
            await callback.message.edit_text(TEXTS[lang]["prediction_saved"])
            logger.info(f"✅ کاربر {tg_id} پیش‌بینی خود را ثبت کرد")
        
        await callback.answer()
    except Exception as e:
        logger.error(f"خطا در process_team: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)

# ============================================
# 🚀 تابع اصلی با مدیریت خطا و Restart خودکار
# ============================================
async def main():
    """تابع اصلی با مدیریت خطا و تلاش مجدد"""
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🚀 تلاش {attempt + 1} برای شروع ربات...")
            
            # ساخت دیتابیس
            if not init_db():
                logger.error("❌ ساخت دیتابیس ناموفق بود")
                continue
            
            # ساخت ربات و dispatcher
            bot = Bot(token=BOT_TOKEN)
            storage = MemoryStorage()
            dp = Dispatcher(storage=storage)
            
            # ثبت هندلرها
            dp.message.register(cmd_start, CommandStart())
            dp.callback_query.register(process_lang, F.data.startswith('lang_'))
            dp.callback_query.register(process_country, F.data.startswith('country_'))
            dp.message.register(process_email, RegStates.email)
            dp.message.register(process_wallet, RegStates.wallet)
            dp.callback_query.register(check_payment, F.data == 'check_payment')
            dp.callback_query.register(process_team, F.data.startswith('team_'))
            
            logger.info("✅ ربات با موفقیت شروع شد!")
            await dp.start_polling(bot)
            
        except Exception as e:
            logger.error(f"❌ خطا در اجرای ربات (تلاش {attempt + 1}): {e}")
            logger.error(traceback.format_exc())
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ تلاش مجدد در {retry_delay} ثانیه...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("❌ تمام تلاش‌ها ناموفق بود. ربات متوقف می‌شود.")
                break

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 ربات توسط کاربر متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطای غیرمنتظره: {e}")
        logger.error(traceback.format_exc())
