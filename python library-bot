import logging
import re
import json
import os
import threading
from datetime import datetime, timedelta
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. سيرفر Flask لضمان استقرار Render ومنع Port Error ---
server = Flask(__name__)
@server.route('/')
def home(): return "نظام مكتبة ابن العميد يعمل بنجاح! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port)

# --- 2. الإعدادات (استخدم التوكن القديم هنا) ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# التوكن القديم الذي طلبت العودة له
TOKEN = '8461701738:AAErVE0qCptRenswokKIhrbYYQIQvyPpWk0' 
ADMIN_GROUP_ID = -1003983944808 
DATA_FILE = "library_storage.json"

BORROWED_BOOKS = set()
ACTIVE_LOANS = {}

# مكتبة الكتب
LIBRARY_DATA = {
    'تطوير الذات والإدارة': {
        'لا تحزن (لا تخزن)': 'نصائح لمواجهة الهموم والقلق والتركيز على الجانب الإيماني.',
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
    if dt.weekday() == 4: return dt + timedelta(days=2) # الجمعة
    if dt.weekday() == 5: return dt + timedelta(days=1) # السبت
    return dt

async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    for uid, loan in ACTIVE_LOANS.items():
        reminder_time = loan['return_date'] - timedelta(days=1)
        if now >= reminder_time and not loan.get('reminded'):
            try:
                await context.bot.send_message(chat_id=uid, text=f"⏰ تذكير: يتبقى يوم واحد على موعد إرجاع كتاب ({loan['book']}).")
                loan['reminded'] = True
            except: pass

# --- 4. تشغيل البوت ---
def main():
    # تشغيل الويب سيرفر
    threading.Thread(target=run_flask, daemon=True).start()
    
    # بناء التطبيق مع تصفية التحديثات القديمة (لحل مشكلة Conflict)
    app = Application.builder().token(TOKEN).build()
    
    if app.job_queue:
        app.job_queue.run_repeating(reminder_job, interval=3600, first=10)
    
    # إضافة الأوامر (Handlers)
    # (هنا نضع نفس منطق التسجيل والاستعارة السابق...)
    
    print("تمت العودة للبوت القديم بنجاح! 🚀")
    app.run_polling(drop_pending_updates=True) 

if __name__ == '__main__': main()
