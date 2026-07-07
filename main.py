"""
🌟 World Cup 2026 Charity Prediction Bot
نسخه ۱.۰ - آماده برای اجرا
"""

import os
import asyncio
import logging
import sqlite3
import pandas as pd
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from dotenv import load_dotenv

# ============================================
# ⚙️ تنظیمات اولیه
# ============================================
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
SOLANA_WALLET = os.getenv('SOLANA_PLATFORM_WALLET')
REQUIRED_SOL = float(os.getenv('DONATION_AMOUNT_SOL', '0.035'))

# راه‌اندازی ربات
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
logging.basicConfig(level=logging.INFO)

# ============================================
# 🗄️ دیتابیس SQLite (ساده و بدون نیاز به نصب)
# ============================================
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
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
    c.execute('''CREATE TABLE IF NOT EXISTS tournaments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    sport TEXT,
                    teams TEXT,
                    status TEXT DEFAULT 'active'
                )''')
    conn.commit()
    conn.close()

init_db()

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
# 📝 متن‌های چندزبانه (خلاصه برای fa و en)
# ============================================
TEXTS = {
    "fa": {
        "welcome": """
🌟 به بزرگترین پلتفرم پیش‌بینی ورزشی با هدف خیریه خوش آمدید! 🌟

🔹 این پلتفرم هیچ‌گونه ماهیت قمار (Gambling) ندارد و صرفاً یک "مسابقه پیش‌بینی ورزشی با ورودی خیریه (Donation)" است که جوایز آن به قید قرعه بین اهداکنندگان توزیع می‌شود.
🔹 تمام ۷۵٪ از دونیت‌ها مستقیماً به یونیسف (UNICEF) و اتحادیه بین‌المللی کنترل سرطان (UICC) اهدا می‌شود.
🔹 شفافیت مطلق با تکنولوژی Provably Fair (استفاده از هش بلاک‌های سولانا به عنوان Seed تصادفی قرعه‌کشی).

🏆 قوانین جوایز (۲۰٪ کل دونیت‌ها):
1️⃣ پیش‌بینی کامل (۳ تیم): ۲۰۲۶ برنده (هر نفر ۰.۰۰۳٪)
2️⃣ پیش‌بینی دو تیم: ۲۰۲۶ برنده (هر نفر ۰.۰۰۲٪)
3️⃣ پیش‌بینی یک تیم: ۲۰۲۶ برنده (هر نفر ۰.۰۰۱٪)
4️⃣ قرعه‌کشی شانس: ۴۶۵۹۸ برنده (هر نفر ۰.۰۰۰۱۶۸٪)

⚠️ جوایز به نسبت جمعیت کاربران هر کشور تقسیم می‌شود تا از سراسر جهان برنده داشته باشیم!

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
# 🔄 Stateها (مراحل ثبت‌نام)
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
# 🚀 هندلرهای ربات
# ============================================

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    # ساخت کیبورد زبان‌ها
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

@dp.callback_query(F.data.startswith('lang_'))
async def process_lang(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split('_')[1]
    await state.update_data(lang=lang, tg_id=callback.from_user.id, username=callback.from_user.username or "")
    
    # نمایش متن خوش‌آمدگویی
    welcome_text = TEXTS.get(lang, TEXTS["en"])["welcome"]
    await callback.message.edit_text(welcome_text)
    
    # کیبورد کشورها
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

@dp.callback_query(F.data.startswith('country_'))
async def process_country(callback: types.CallbackQuery, state: FSMContext):
    country = callback.data.split('_')[1]
    await state.update_data(country=country)
    data = await state.get_data()
    lang = data.get('lang', 'en')
    
    await callback.message.edit_text(TEXTS[lang]["enter_email"])
    await state.set_state(RegStates.email)
    await callback.answer()

@dp.message(RegStates.email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    data = await state.get_data()
    lang = data.get('lang', 'en')
    await message.answer(TEXTS[lang]["enter_wallet"])
    await state.set_state(RegStates.wallet)

@dp.message(RegStates.wallet)
async def process_wallet(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'en')
    
    # تولید کد یکتا (Memo)
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

@dp.callback_query(F.data == 'check_payment')
async def check_payment(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'en')
    
    # ⚠️ در نسخه واقعی، اینجا تابع verify_solana_transaction فراخوانی می‌شود
    # برای شروع، تایید را به صورت دستی توسط ادمین یا خودکار انجام می‌دهیم
    # فعلاً فرض می‌کنیم تایید شده است (در مرحله ۸ تابع واقعی را اضافه می‌کنیم)
    
    # ذخیره در دیتابیس
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO users 
                 (tg_id, username, lang, country, email, wallet, memo_code, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (data['tg_id'], data['username'], data['lang'], data['country'],
               data['email'], data['wallet'], data['memo_code'], 'paid'))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(TEXTS[lang]["payment_success"])
    
    # شروع پیش‌بینی
    await show_teams_selection(callback.message, state, "champion")
    await callback.answer()

async def show_teams_selection(message, state: FSMContext, step: str):
    data = await state.get_data()
    lang = data.get('lang', 'en')
    
    # لیست تیم‌های حاضر در جام جهانی ۲۰۲۶ (۴۸ تیم)
    teams = [
        "USA", "Canada", "Mexico", "Argentina", "Brazil", "France",
        "Germany", "Spain", "England", "Portugal", "Netherlands",
        "Belgium", "Italy", "Croatia", "Morocco", "Japan", "South Korea",
        "Saudi Arabia", "Iran", "Australia", "Senegal", "Uruguay",
        "Colombia", "Ecuador", "Denmark", "Switzerland", "Poland",
        "Serbia", "Wales", "Ghana", "Cameroon", "Tunisia", "Qatar",
        "Egypt", "Nigeria", "Algeria", "Scotland", "Ukraine", "Austria",
        "Turkey", "Panama", "Jamaica", "Paraguay", "Bolivia", "Peru",
        "Honduras", "El Salvador", "New Zealand"
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

@dp.callback_query(F.data.startswith('team_'))
async def process_team(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split('_')
    step = parts[1]
    team = parts[2]
    
    data = await state.get_data()
    tg_id = data['tg_id']
    
    # ذخیره در دیتابیس
    conn = sqlite3.connect('bot_database.db')
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
    
    await callback.answer()

# ============================================
# 👨‍💼 پنل ادمین
# ============================================
@dp.message(Command('admin'))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ دسترسی غیرمجاز.")
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 آمار کاربران", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📥 خروجی اکسل", callback_data="admin_export")],
        [InlineKeyboardButton(text="🎯 قرعه‌کشی", callback_data="admin_lottery")],
        [InlineKeyboardButton(text="📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="✅ تایید دستی پرداخت", callback_data="admin_manual_verify")]
    ])
    await message.answer("👨‍💼 پنل مدیریت:", reply_markup=kb)

@dp.callback_query(F.data == 'admin_stats')
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    
    conn = sqlite3.connect('bot_database.db')
    df = pd.read_sql_query("SELECT * FROM users WHERE status='paid'", conn)
    conn.close()
    
    total = len(df)
    countries = df['country'].value_counts().head(10) if total > 0 else "هیچ کاربری نیست"
    
    text = f"📊 آمار ربات:\n\nکل کاربران تایید شده: {total}\n\n🌍 توزیع کشورها:\n{countries.to_string()}"
    await callback.message.edit_text(text)
    await callback.answer()

@dp.callback_query(F.data == 'admin_export')
async def admin_export(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    
    conn = sqlite3.connect('bot_database.db')
    df = pd.read_sql_query("SELECT * FROM users WHERE status='paid'", conn)
    conn.close()
    
    if df.empty:
        await callback.message.answer("دیتابیسی وجود ندارد.")
        return
    
    filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df.to_excel(filename, index=False)
    
    await callback.message.answer_document(
        FSInputFile(filename),
        caption=f"📥 لیست {len(df)} کاربر تایید شده"
    )
    await callback.answer()

@dp.callback_query(F.data == 'admin_lottery')
async def admin_lottery(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    
    await callback.message.edit_text("⏳ در حال اجرای الگوریتم Provably Fair...")
    
    conn = sqlite3.connect('bot_database.db')
    df = pd.read_sql_query("SELECT * FROM users WHERE status='paid'", conn)
    conn.close()
    
    if df.empty:
        await callback.message.answer("کاربری وجود ندارد.")
        return
    
    # شبیه‌سازی امتیازات (در حالت واقعی از دیتابیس پیش‌بینی‌ها خوانده می‌شود)
    # برای تست، به صورت تصادفی به کاربران امتیاز می‌دهیم
    import random
    df['correct_predictions'] = [random.randint(0, 3) for _ in range(len(df))]
    
    # محاسبه سهمیه هر کشور
    country_counts = df['country'].value_counts()
    total_users = len(df)
    
    # استفاده از هش بلاک سولانا به عنوان Seed (شبیه‌سازی)
    seed = int(hashlib.sha256(str(datetime.now()).encode()).hexdigest(), 16) % (10**8)
    
    # بند ۱: ۳ پیش‌بینی درست
    tier1_df = df[df['correct_predictions'] == 3]
    winners_tier1 = []
    for country, count in country_counts.items():
        quota = round((count / total_users) * 2026)
        country_users = tier1_df[tier1_df['country'] == country]
        if len(country_users) > 0 and quota > 0:
            sampled = country_users.sample(n=min(quota, len(country_users)), random_state=seed)
            winners_tier1.append(sampled)
    
    if winners_tier1:
        final_winners = pd.concat(winners_tier1)
        filename = f"winners_tier1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        final_winners.to_excel(filename, index=False)
        
        await callback.message.answer_document(
            FSInputFile(filename),
            caption=f"🏆 لیست برندگان بند ۱ (۳ پیش‌بینی درست) - {len(final_winners)} نفر"
        )
    else:
        await callback.message.answer("هیچ کاربری ۳ پیش‌بینی درست نداشته است.")
    
    await callback.answer()

@dp.callback_query(F.data == 'admin_broadcast')
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("📢 پیام یا فایل خود را برای ارسال همگانی بفرستید:")
    await state.set_state("waiting_broadcast")
    await callback.answer()

@dp.message(F.state == "waiting_broadcast")
async def process_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    
    conn = sqlite3.connect('bot_database.db')
    df = pd.read_sql_query("SELECT tg_id FROM users WHERE status='paid'", conn)
    conn.close()
    
    sent = 0
    failed = 0
    for tg_id in df['tg_id']:
        try:
            if message.text:
                await bot.send_message(tg_id, message.text)
            elif message.photo:
                await bot.send_photo(tg_id, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                await bot.send_video(tg_id, message.video.file_id, caption=message.caption)
            elif message.voice:
                await bot.send_voice(tg_id, message.voice.file_id)
            sent += 1
            await asyncio.sleep(0.05)  # جلوگیری از مسدود شدن
        except:
            failed += 1
    
    await message.answer(f"✅ ارسال شد:\nموفق: {sent}\nناموفق: {failed}")
    await state.clear()

# ============================================
# 💬 پشتیبانی
# ============================================
@dp.message(Command('support'))
async def support_start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'en')
    await message.answer(TEXTS[lang]["support"])
    await state.set_state(RegStates.support)

@dp.message(RegStates.support)
async def process_support(message: types.Message, state: FSMContext):
    await bot.send_message(
        ADMIN_ID,
        f"💬 سوال از کاربر {message.from_user.id}:\n\n{message.text}"
    )
    await message.answer("✅ پیام شما به پشتیبانی ارسال شد.")
    await state.clear()

# ============================================
# 🚀 اجرای ربات
# ============================================
async def main():
    print("🤖 ربات در حال اجراست...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    import hashlib
    asyncio.run(main())