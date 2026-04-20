import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from flask import Flask
import threading
import os
from datetime import datetime

# 1. إعداد Flask (ضروري جداً لمنصة Render)
app = Flask(__name__)

@app.route('/')
def home():
    return "نظام مكتبة ابن العميد يعمل بنجاح! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. إعدادات البوت والبيانات
TOKEN = '8461701738:AAErVE0qCptRenswokKIhrbYYQIQvyPpWk0'
ADMIN_GROUP_ID = -1003983944808 

# قائمة كتب مكتبة ابن العميد الأصلية مقسمة حسب طلبك
LIBRARY_DATA = {
    'تطوير الذات والإدارة': {
        'لا تحزن': 'نصائح لمواجهة الهموم والقلق والتركيز على الجانب الإيماني.',
        'مشوار الإصرار والتحدي': 'قصص ومواقف تحفزك على التمسك بأهدافك رغم الصعوبات.',
        'ركز': 'تعلم كيف تبتعد عن المشتتات وتوجه انتباهك الكامل لمهمة واحدة.'
    },
    'سلسلة آفاق العلمية': {
        'الطاقة المتجددة': 'كيفية استخراج الكهرباء من الشمس والرياح والماء.',
        'القوة المحركة': 'المحركات والآلات وكيف تتحول الطاقة إلى حركة.'
    },
    'العلوم الشرعية والتاريخ': {
        'السيرة النبوية': 'قصة حياة الرسول ﷺ بأسلوب تاريخي ممتع.',
        'تفسير العشر الأخير': 'شرح ميسر وبسيط لمعاني سور القرآن الكريم.'
    }
}

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "📚 أهلاً بك في بوت مكتبة مدرسة ابن العميد ✨\n\n"
        "للبدء، من فضلك أرسل **اسمك الثلاثي**:"
    )
    chat_id = update.effective_chat.id
    user_data[chat_id] = {} # تصفير البيانات للبدء من جديد
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if chat_id not in user_data or 'full_name' not in user_data[chat_id]:
        user_data[chat_id] = {'full_name': text}
        await update.message.reply_text("جميل! الآن أرسل **الصف والشعبة** (مثال: 3/1):")
    
    elif 'class' not in user_data[chat_id]:
        user_data[chat_id]['class'] = text
        await update.message.reply_text("أرسل الآن **رقم جوالك** للتواصل:")
        
    elif 'phone' not in user_data[chat_id]:
        user_data[chat_id]['phone'] = text
        # عرض الأقسام الرئيسية بعد اكتمال البيانات
        keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in LIBRARY_DATA.keys()]
        await update.message.reply_text("تم تسجيل بياناتك! ✅\nاختر الآن القسم الذي تريد تصفحه:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    else:
        await update.message.reply_text("يرجى اختيار كتاب من القائمة أو كتابة /start للبدء من جديد.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("cat_"):
        cat_name = data.split("_", 1)[1]
        context.user_data['current_cat'] = cat_name
        buttons = [[InlineKeyboardButton(f"📖 {book}", callback_data=f"info_{book}")] for book in LIBRARY_DATA[cat_name].keys()]
        await query.edit_message_text(f"📚 كتب قسم {cat_name}:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("info_"):
        book_name = data.split("_", 1)[1]
        cat = context.user_data.get('current_cat')
        desc = LIBRARY_DATA[cat][book_name]
        keyboard = [[InlineKeyboardButton("✅ تأكيد طلب الاستعارة", callback_data=f"rent_{book_name}")]]
        await query.edit_message_text(f"📖 **{book_name}**\n\n📝 {desc}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("rent_"):
        book_title = data.split("_", 1)[1]
        student = user_data.get(query.message.chat_id, {})
        
        # إرسال البيانات للإدارة
        admin_msg = (
            "🚨 **طلب استعارة جديد** 🚨\n\n"
            f"👤 **الطالب:** {student.get('full_name')}\n"
            f"🏫 **الصف:** {student.get('class')}\n"
            f"📞 **الجوال:** {student.get('phone')}\n"
            f"📚 **الكتاب:** {book_title}\n"
            f"📅 **التاريخ:** {datetime.now().strftime('%Y/%m/%d')}"
        )
        
        try:
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_msg)
            await query.edit_message_text(text=f"شكراً لك! تم إرسال طلبك لاستعارة '{book_title}' للإدارة. يرجى مراجعة المكتبة لاستلام الكتاب.")
        except:
            await query.edit_message_text(text="حدث خطأ في الإرسال، تأكد من وجود البوت في جروب الإدارة.")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    application.run_polling(drop_pending_updates=True)
