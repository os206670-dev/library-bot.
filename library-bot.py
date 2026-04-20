import logging
import re
import json
import os
import threading
from datetime import datetime, timedelta
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. إعداد الويب سيرفر (Flask) لحل مشكلة المنفذ في Render ---
server = Flask(__name__)

@server.route('/')
def home():
    return "نظام مكتبة ابن العميد يعمل بنجاح! 🚀"

def run_flask():
    # Render يمرر المنفذ عبر متغير PORT، وإذا لم يوجد نستخدم 8080
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port)

# --- 2. إعدادات التسجيل والبيانات الأساسية ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# التوكن الجديد الذي أرسلته
TOKEN = '8461701738:AAHpwds61QTCy5dSLH9cDm2uk5a_Ng6li1w' 
ADMIN_GROUP_ID = -1003983944808 
DATA_FILE = "library_storage.json"

BORROWED_BOOKS = set()
ACTIVE_LOANS = {}

# قائمة كتب مكتبة مدرسة ابن العميد
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

# --- 3. وظائف إدارة البيانات (حفظ وتحميل) ---
def save_data():
    serializable_loans = {}
    for uid, loan in ACTIVE_LOANS.items():
        copy_loan = loan.copy()
        copy_loan['date'] = loan['date'].isoformat()
        copy_loan['return_date'] = loan['return_date'].isoformat()
        serializable_loans[str(uid)] = copy_loan
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"BORROWED_BOOKS": list(BORROWED_BOOKS), "ACTIVE_LOANS": serializable_loans}, f, ensure_ascii=False, indent=4)

def load_data():
    global BORROWED_BOOKS, ACTIVE_LOANS
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                BORROWED_BOOKS = set(data.get("BORROWED_BOOKS", []))
                raw_loans = data.get("ACTIVE_LOANS", {})
                ACTIVE_LOANS = {int(uid): {**l, 'date': datetime.fromisoformat(l['date']), 'return_date': datetime.fromisoformat(l['return_date'])} for uid, l in raw_loans.items()}
        except: pass

def format_date(dt):
    days = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
    return f"{days[dt.weekday()]} {dt.strftime('%Y/%m/%d')}"

# --- 4. معالجات البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_data()
    user_id = update.effective_user.id
    if user_id in ACTIVE_LOANS:
        loan = ACTIVE_LOANS[user_id]
        kb = [[InlineKeyboardButton("📥 طلب إرجاع الكتاب", callback_data="req_ret")]]
        await update.message.reply_text(f"أهلاً بك مجدداً!\n\nأنت تستعير: {loan['book']}\nموعد الإرجاع: {format_date(loan['return_date'])}", reply_markup=InlineKeyboardMarkup(kb))
        return
    
    await update.message.reply_text("✨ مكتبة ابن العميد ترحب بك\n\nيرجى إرسال اسمك الثلاثي للبدء:")
    context.user_data['step'] = 'NAME'

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get('step')
    if not step: return
    text = update.message.text.strip()
    
    if step == 'NAME':
        context.user_data['student_name'] = text
        await update.message.reply_text("📍 أرسل فصلك الدراسي (مثال: 3/1):")
        context.user_data['step'] = 'CLASS'
    elif step == 'CLASS':
        context.user_data['student_class'] = text
        await update.message.reply_text("📞 أرسل رقم جوالك:")
        context.user_data['step'] = 'PHONE'
    elif step == 'PHONE':
        if re.match(r'^0\d{9}$', text):
            context.user_data['student_phone'] = text
            context.user_data['step'] = 'DONE'
            kb = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in LIBRARY_DATA.keys()]
            await update.message.reply_text("✅ تم التسجيل. اختر قسماً لتصفح الكتب:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_text("❌ أرسل رقم جوال صحيح يبدأ بـ 0 ومكون من 10 أرقام:")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("cat_"):
        cat = data.split("_", 1)[1]
        context.user_data['current_cat'] = cat
        buttons = [[InlineKeyboardButton(f"{'🔴' if b in BORROWED_BOOKS else '🟢'} {b}", callback_data=f"info_{b}")] for b in LIBRARY_DATA[cat].keys()]
        buttons.append([InlineKeyboardButton("🔙 الأقسام", callback_data="back_to_cats")])
        await query.edit_message_text(f"📚 كتب {cat}:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("info_"):
        book = data.split("_", 1)[1]
        cat = context.user_data.get('current_cat')
        desc = LIBRARY_DATA[cat][book]
        kb = [[InlineKeyboardButton("✅ استعارة", callback_data=f"brw_{book}")]] if book not in BORROWED_BOOKS and user_id not in ACTIVE_LOANS else [[InlineKeyboardButton("🔙 رجوع", callback_data=f"cat_{cat}")]]
        await query.edit_message_text(f"📖 {book}\n\n{desc}", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("brw_"):
        book = data.split("_", 1)[1]
        now = datetime.now()
        ret = now + timedelta(days=7)
        BORROWED_BOOKS.add(book)
        ACTIVE_LOANS[user_id] = {'book': book, 'name': context.user_data.get('student_name'), 'class': context.user_data.get('student_class'), 'phone': context.user_data.get('student_phone'), 'date': now, 'return_date': ret}
        save_data()
        await query.edit_message_text(f"✅ تمت الاستعارة بنجاح!\nكتاب: {book}\nموعد الإرجاع: {format_date(ret)}")
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"🔔 طلب استعارة جديد:\n👤 الطالب: {ACTIVE_LOANS[user_id]['name']}\n📖 الكتاب: {book}\n📞 الجوال: {ACTIVE_LOANS[user_id]['phone']}")

    elif data == "back_to_cats":
        kb = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in LIBRARY_DATA.keys()]
        await query.edit_message_text("اختر القسم:", reply_markup=InlineKeyboardMarkup(kb))

# --- 5. تشغيل التطبيق (البوت + السيرفر) ---
def main():
    load_data()
    # تشغيل Flask في خيط منفصل لحل مشكلة المنفذ في Render
    threading.Thread(target=run_flask, daemon=True).start()
    
    # استخدام drop_pending_updates=True لتنظيف أي طلبات قديمة متعارضة
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("نظام مكتبة ابن العميد انطلق بنجاح!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
    
