import os
import threading
import logging
from flask import Flask
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# إعداد السجلات لمراقبة البوت
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- 1. سيرفر Flask الصغير لإبقاء الخدمة حية على Render ---
server = Flask(__name__)
@server.route('/')
def home(): return "نظام مكتبة ابن العميد يعمل بنجاح! 🚀"

def run_flask():
    # Render يحتاج لربط البورت (Port Binding) ليعتبر الخدمة Live
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port)

# --- 2. إعدادات البوت ---
TOKEN = '8461701738:AAErVE0qCptRenswokKIhrbYYQIQvyPpWk0'

async def start(update, context):
    await update.message.reply_text("📚 أهلاً بك في مكتبة ابن العميد!\nالنظام الآن يعمل بشكل كامل ومستقر.")

# --- 3. تشغيل البوت ---
def main():
    # تشغيل Flask في الخلفية (تم حل مشكلة تعريف threading هنا)
    threading.Thread(target=run_flask, daemon=True).start()

    # بناء البوت
    app = Application.builder().token(TOKEN).build()
    
    # إضافة الأوامر
    app.add_handler(CommandHandler("start", start))
    
    print("انطلق البوت بنسخة الاستقرار النهائية...")
    
    # استخدام drop_pending_updates=True لمنع التعارض عند إعادة التشغيل
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
