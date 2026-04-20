import logging
import re
import json
import os
import threading
from datetime import datetime, timedelta
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. إعداد الويب سيرفر (Flask) لضمان استقرار Render ---
server = Flask(__name__)
@server.route('/')
def home(): return "نظام مكتبة ابن العميد يعمل بنجاح! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port)

# --- 2. الإعدادات والبيانات ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# التوكن القديم المستهدف
TOKEN = '8461701738:AAErVE0qCptRenswokKIhrbYYQIQvyPpWk0' 
ADMIN_GROUP_ID = -1003983944808 
DATA_FILE = "library_storage.json"

BORROWED_BOOKS = set()
ACTIVE_LOANS = {}

# مكتبة الكتب الكاملة
LIBRARY_DATA = {
    'تطوير الذات والإدارة': {
        'لا تحزن (لا تخزن)': 'نصائح لمواجهة الهموم والقلق والتركيز على الجانب الإيماني.',
        'مشوار الإصرار والتحدي': 'قصص ومواقف تحفزك على التمسك بأهدافك رغم الصعوبات.',
        'ركز': 'تعلم كيف تبتعد عن المشتتات وتوجه انتباهك الكامل لمهمة واحدة.',
        'أول قاعدتين بالقيادة': 'صفات القائد الناجح: كن قدوة، واهتم بفريقك.',
        'عندما تكون ناجياً ومحباً': 'النجاح المتوازن بين الإنجاز والراحة النفسية.'
    },
    'سلسلة آفاق العلمية': {
        'الطاقة المتجددة': 'كيفية استخراج الكهرباء من الشمس والرياح والماء.',
        'القوة المحركة': 'المحركات والآلات وكيف تتحول الطاقة إلى حركة.',
        'الأبنية': 'هندسة البناء من البيوت البسيطة إلى ناطحات السحاب.'
    },
    'العلوم الشرعية والتاريخ': {
        'السيرة النبوية': 'قصة حياة الرسول ﷺ بأسلوب تاريخي ممتع.',
        'الصحيح': 'مرجع للأحاديث النبوية الصحيحة.',
        'تفسير العشر الأخير': 'شرح ميسر وبسيط لمعاني سور القرآن الكريم.'
    },
    'روايات وكتب أدبية': {
        'آفاق بلا حدود': 'طموح الإنسان وقدراته غير المحدودة.',
        'اللوحة القتالية': 'عمل أدبي يتناول التحديات بأسلوب درامي مشوق.',
        'قفص الموت الغامض': 'رواية إثارة وغموض تتطلب ذكاءً وتركيزاً.'
    }
}

# --- 3. إدارة التواريخ والعطلات والتذكير ---
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

# --- 4. منطق البوت (التسجيل والاستعارة) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in ACTIVE_LOANS:
        loan = ACTIVE_LOANS[user_id]
        kb = [[InlineKeyboardButton("📥 طلب إرجاع الكتاب", callback_data="req_ret")]]
        if not loan.get('extended'):
            kb.append([InlineKeyboardButton("⏳ تمديد أسبوع إضافي", callback_data="extend_loan")])
        await update.message.reply_text(f"✨ مرحباً بك مجدداً!\nأنت تستعير حالياً: {loan['book']}\nموعد الإرجاع: {loan['return_date'].strftime('%Y/%m/%d')}", reply_markup=InlineKeyboardMarkup(kb))
        return
    await update.message.reply_text("📚 أهلاً بك في نظام مكتبة ابن العميد!\nمن فضلك، أرسل **اسمك الثلاثي** للبدء:")
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
        await update.message.reply_text("📞 أرسل **رقم جوالك** للتواصل:")
        context.user_data['step'] = 'PHONE'
    elif step == 'PHONE':
        if re.match(r'^0\d{9}$', text):
            context.user_data['student_phone'] = text
            kb = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in LIBRARY_DATA.keys()]
            await update.message.reply_text("✅ تم التسجيل. اختر قسماً للتصفح:", reply_markup=InlineKeyboardMarkup(kb))
        else: await update.message.reply_text("❌ أرسل 10 أرقام تبدأ بـ 0:")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data, user_id = query.data, query.from_user.id

    if data.startswith("cat_"):
        cat = data.split("_", 1)[1]
        context.user_data['current_cat'] = cat
        buttons = [[InlineKeyboardButton(f"{'🔴' if b in BORROWED_BOOKS else '🟢'} {b}", callback_data=f"info_{b}")] for b in LIBRARY_DATA[cat].keys()]
        await query.edit_message_text(f"📚 كتب قسم {cat}:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("info_"):
        book = data.split("_", 1)[1]
        kb = [[InlineKeyboardButton("✅ طلب استعارة", callback_data=f"terms_{book}")]] if book not in BORROWED_BOOKS else [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_cats")]]
        await query.edit_message_text(f"📖 {book}\n{LIBRARY_DATA[context.user_data['current_cat']][book]}", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("terms_"):
        book = data.split("_", 1)[1]
        kb = [[InlineKeyboardButton("✅ أوافق", callback_data=f"brw_{book}")], [InlineKeyboardButton("❌ إلغاء", callback_data="back_to_cats")]]
        await query.edit_message_text(f"⚠️ **شروط الاستعارة:** الحفاظ على الكتاب والالتزام بالموعد. هل توافق؟", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("brw_"):
        book = data.split("_", 1)[1]
        ret = adjust_for_weekend(datetime.now() + timedelta(days=7))
        BORROWED_BOOKS.add(book)
        ACTIVE_LOANS[user_id] = {'book': book, 'name': context.user_data['student_name'], 'class': context.user_data['student_class'], 'return_date': ret, 'extended': False}
        await query.edit_message_text(f"✅ تمت الاستعارة!\nالموعد: {ret.strftime('%Y/%m/%d')}")
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
    
    print("البوت ينطلق الآن...")
    app.run_polling(drop_pending_updates=True) # حل مشكلة Conflict

if __name__ == '__main__': main()
