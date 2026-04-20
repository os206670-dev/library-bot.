import logging
import re
import json
import os
import threading
from datetime import datetime, timedelta
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. سيرفر Flask لضمان استقرار Render ومنع خطأ الـ Port ---
server = Flask(__name__)
@server.route('/')
def home(): return "نظام مكتبة ابن العميد يعمل بنجاح! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port)

# --- 2. الإعدادات والبيانات ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# التوكن القديم الذي طلبت العودة إليه
TOKEN = '8461701738:AAErVE0qCptRenswokKIhrbYYQIQvyPpWk0' 
ADMIN_GROUP_ID = -1003983944808 
DATA_FILE = "library_storage.json"

BORROWED_BOOKS = set()
ACTIVE_LOANS = {}

# مكتبة الكتب (مدرسة ابن العميد)
LIBRARY_DATA = {
    'تطوير الذات والإدارة': {
        'لا تحزن (لا تخزن)': 'نصائح لمواجهة الهموم والقلق والمركز على الجانب الإيماني.',
        'مشوار الإصرار والتحدي': 'قصص ومواقف تحفزك على التمسك بأهدافك رغم الصعوبات.',
        'ركز': 'تعلم كيف تبتعد عن المشتتات وتوجه انتباهك الكامل لمهمة واحدة.'
    },
    'سلسلة آفاق العلمية': {
        'الطاقة المتجددة': 'كيفية استخراج الكهرباء من الشمس والرياح والماء.',
        'القوة المحركة': 'المحركات والآلات وكيف تتحول الطاقة إلى حركة.'
    }
}

# --- 3. إدارة التواريخ والتذكير ---
def adjust_for_weekend(dt):
    if dt.weekday() == 4: return dt + timedelta(days=2) # الجمعة -> الأحد
    if dt.weekday() == 5: return dt + timedelta(days=1) # السبت -> الأحد
    return dt

async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    for uid, loan in list(ACTIVE_LOANS.items()):
        reminder_time = loan['return_date'] - timedelta(days=1)
        if now >= reminder_time and not loan.get('reminded'):
            try:
                await context.bot.send_message(chat_id=uid, text=f"⏰ **تذكير:** غداً موعد إرجاع كتاب ({loan['book']}).")
                loan['reminded'] = True
            except: pass

# --- 4. منطق البوت (الترحيب، الاستعارة، الإدارة) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in ACTIVE_LOANS:
        loan = ACTIVE_LOANS[user_id]
        kb = [[InlineKeyboardButton("📥 طلب إرجاع الكتاب", callback_data="req_ret")]]
        if not loan.get('extended'):
            kb.append([InlineKeyboardButton("⏳ تمديد أسبوع إضافي", callback_data="extend_loan")])
        await update.message.reply_text(f"✨ مرحباً بك مجدداً!\nأنت تستعير: {loan['book']}", reply_markup=InlineKeyboardMarkup(kb))
        return
    await update.message.reply_text("📚 أهلاً بك في مكتبة ابن العميد!\nأرسل **اسمك الثلاثي** للبدء:")
    context.user_data['step'] = 'NAME'

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get('step')
    if not step: return
    text = update.message.text.strip()
    if step == 'NAME':
        context.user_data['student_name'] = text
        await update.message.reply_text("📍 أرسل **الصف والشعبة** (مثال: 3/1):")
        context.user_data['step'] = 'CLASS'
    elif step == 'CLASS':
        context.user_data['student_class'] = text
        kb = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in LIBRARY_DATA.keys()]
        await update.message.reply_text("✅ اختر قسماً لتصفح الكتب:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data, user_id = query.data, query.from_user.id

    if data.startswith("cat_"):
        cat = data.split("_", 1)[1]
        context.user_data['current_cat'] = cat
        buttons = [[InlineKeyboardButton(f"🟢 {b}", callback_data=f"info_{b}")] for b in LIBRARY_DATA[cat].keys()]
        await query.edit_message_text(f"📚 كتب قسم {cat}:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("info_"):
        book = data.split("_", 1)[1]
        kb = [[InlineKeyboardButton("✅ استعارة", callback_data=f"brw_{book}")]]
        await query.edit_message_text(f"📖 {book}\n{LIBRARY_DATA[context.user_data['current_cat']][book]}", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("brw_"):
        book = data.split("_", 1)[1]
        ret = adjust_for_weekend(datetime.now() + timedelta(days=7))
        ACTIVE_LOANS[user_id] = {'book': book, 'name': context.user_data['student_name'], 'class': context.user_data['student_class'], 'return_date': ret, 'extended': False}
        await query.edit_message_text(f"✅ تمت الاستعارة! موعد الإرجاع: {ret.strftime('%Y/%m/%d')}")
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"🔔 استعارة جديدة: {context.user_data['student_name']} - {book}")

# --- 5. التشغيل النهائي ---
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    
    # حل مشكلة AttributeError: NoneType
    if app.job_queue:
        app.job_queue.run_repeating(reminder_job, interval=3600, first=10)
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # حل مشكلة Conflict وتراكم الرسائل
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__': main()
