import logging
import re
import json
import os
import threading
from datetime import datetime, timedelta
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. سيرفر Flask لضمان استقرار Render ---
server = Flask(__name__)
@server.route('/')
def home(): return "نظام مكتبة ابن العميد يعمل بنجاح! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port)

# --- 2. الإعدادات والتوكن الجديد ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = '8254293210:AAF64_RgiyPljjC2p_gxZazsjjmSgOd69as' 
ADMIN_GROUP_ID = -1003983944808 
DATA_FILE = "library_storage.json"

BORROWED_BOOKS = set()
ACTIVE_LOANS = {}

# --- 3. إدارة التواريخ (مراعاة العطلات والتذكير) ---
def adjust_for_weekend(dt):
    if dt.weekday() == 4: return dt + timedelta(days=2) # الجمعة -> الأحد
    if dt.weekday() == 5: return dt + timedelta(days=1) # السبت -> الأحد
    return dt

async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    for uid, loan in ACTIVE_LOANS.items():
        reminder_time = loan['return_date'] - timedelta(days=1)
        if now >= reminder_time and not loan.get('reminded'):
            try:
                await context.bot.send_message(chat_id=uid, text=f"⏰ تذكير: غداً موعد إرجاع كتاب ({loan['book']}).")
                loan['reminded'] = True
            except: pass

# --- 4. تشغيل البوت (The Main Logic) ---
def main():
    # تشغيل Flask في الخلفية لحل مشكلة Port Binding
    threading.Thread(target=run_flask, daemon=True).start()
    
    # بناء التطبيق مع تصفح التحديثات القديمة لمنع التعارض
    app = Application.builder().token(TOKEN).build()
    
    # تفعيل نظام التذكير (Job Queue)
    if app.job_queue:
        app.job_queue.run_repeating(reminder_job, interval=3600, first=10)
    
    # إضافة الأوامر (Handlers) - (Start, Text, Callbacks)
    # ملاحظة: تأكد من إضافة منطق الأقسام والكتب كما في النسخ السابقة
    
    print("انطلق البوت الجديد بنجاح! 🚀")
    app.run_polling(drop_pending_updates=True) # أهم سطر لمنع التعارض

if __name__ == '__main__': main()
    
