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
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = '8461701738:AAHpwds61QTCy5dSLH9cDm2uk5a_Ng6li1w' 
ADMIN_GROUP_ID = -1003983944808 
DATA_FILE = "library_storage.json"

BORROWED_BOOKS = set()
ACTIVE_LOANS = {}

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

# --- 3. إدارة البيانات والتواريخ ---
def save_data():
    serializable_loans = {str(uid): {**l, 'date': l['date'].isoformat(), 'return_date': l['return_date'].isoformat()} for uid, l in ACTIVE_LOANS.items()}
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"BORROWED_BOOKS": list(BORROWED_BOOKS), "ACTIVE_LOANS": serializable_loans}, f, ensure_ascii=False, indent=4)

def load_data():
    global BORROWED_BOOKS, ACTIVE_LOANS
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                BORROWED_BOOKS = set(data.get("BORROWED_BOOKS", []))
                ACTIVE_LOANS = {int(uid): {**l, 'date': datetime.fromisoformat(l['date']), 'return_date': datetime.fromisoformat(l['return_date'])} for uid, l in data.get("ACTIVE_LOANS", {}).items()}
        except: pass

def format_date(dt):
    days = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
    return f"{days[dt.weekday()]} {dt.strftime('%Y/%m/%d')}"

def adjust_for_weekend(dt):
    if dt.weekday() == 4: return dt + timedelta(days=2) 
    if dt.weekday() == 5: return dt + timedelta(days=1) 
    return dt

# --- 4. نظام التذكير المحدث ---
async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    for uid, loan in ACTIVE_LOANS.items():
        reminder_time = loan['return_date'] - timedelta(days=1)
        if now >= reminder_time and not loan.get('reminded'):
            try:
                await context.bot.send_message(chat_id=uid, text=f"⏰ **تذكير:** يتبقى يوم واحد على موعد إرجاع كتاب: ({loan['book']}).")
                loan['reminded'] = True
                save_data()
            except: pass

# --- 5. منطق البوت التفاعلي ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_data()
    user_id = update.effective_user.id
    if user_id in ACTIVE_LOANS:
        loan = ACTIVE_LOANS[user_id]
        kb = [[InlineKeyboardButton("📥 طلب إرجاع الكتاب", callback_data="req_ret")]]
        if not loan.get('extended'):
            kb.append([InlineKeyboardButton("⏳ تمديد أسبوع إضافي", callback_data="extend_loan")])
        await update.message.reply_text(f"✨ مرحباً بك مجدداً!\n\nأنت تستعير: {loan['book']}\nالموعد: {format_date(loan['return_date'])}", reply_markup=InlineKeyboardMarkup(kb))
        return
    await update.message.reply_text("📚 أهلاً بك في نظام مكتبة ابن العميد الذكي\n\nمن فضلك، أرسل **اسمك الثلاثي** للبدء:")
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
        await update.message.reply_text("📞 أرسل **رقم جوالك**:")
        context.user_data['step'] = 'PHONE'
    elif step == 'PHONE':
        if re.match(r'^0\d{9}$', text):
            context.user_data['student_phone'] = text
            context.user_data['step'] = 'DONE'
            kb = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in LIBRARY_DATA.keys()]
            await update.message.reply_text("✅ تم التسجيل. اختر قسماً:", reply_markup=InlineKeyboardMarkup(kb))
        else: await update.message.reply_text("❌ أرسل 10 أرقام تبدأ بـ 0:")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data, user_id = query.data, query.from_user.id

    if data.startswith("cat_"):
        cat = data.split("_", 1)[1]
        context.user_data['current_cat'] = cat
        buttons = [[InlineKeyboardButton(f"{'🔴' if b in BORROWED_BOOKS else '🟢'} {b}", callback_data=f"info_{b}")] for b in LIBRARY_DATA[cat].keys()]
        buttons.append([InlineKeyboardButton("🔙 العودة", callback_data="back_to_cats")])
        await query.edit_message_text(f"📚 كتب قسم {cat}:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("info_"):
        book = data.split("_", 1)[1]
        desc = LIBRARY_DATA[context.user_data['current_cat']][book]
        kb = [[InlineKeyboardButton("✅ استعارة", callback_data=f"terms_{book}")]] if book not in BORROWED_BOOKS and user_id not in ACTIVE_LOANS else [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_cats")]]
        await query.edit_message_text(f"📖 {book}\n\n{desc}", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("terms_"):
        book = data.split("_", 1)[1]
        terms = "⚠️ **شروط الاستعارة:**\n1- الالتزام بالموعد.\n2- الحفاظ على الكتاب.\n3- التعويض في حال التلف.\n\nهل توافق؟"
        kb = [[InlineKeyboardButton("✅ أوافق", callback_data=f"brw_{book}")], [InlineKeyboardButton("❌ إلغاء", callback_data="back_to_cats")]]
        await query.edit_message_text(terms, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data.startswith("brw_"):
        book = data.split("_", 1)[1]
        ret = adjust_for_weekend(datetime.now() + timedelta(days=7))
        BORROWED_BOOKS.add(book)
        ACTIVE_LOANS[user_id] = {'book': book, 'name': context.user_data['student_name'], 'class': context.user_data['student_class'], 'phone': context.user_data['student_phone'], 'date': datetime.now(), 'return_date': ret, 'extended': False, 'reminded': False}
        save_data()
        await query.edit_message_text(f"✅ تمت الاستعارة!\nالموعد: {format_date(ret)}")
        admin_info = f"🔔 **استعارة جديدة**\n👤 {ACTIVE_LOANS[user_id]['name']}\n📍 {ACTIVE_LOANS[user_id]['class']}\n📖 {book}\n📞 {ACTIVE_LOANS[user_id]['phone']}"
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_info, parse_mode='Markdown')

    elif data == "extend_loan":
        loan = ACTIVE_LOANS.get(user_id)
        if loan and not loan.get('extended'):
            loan['return_date'] = adjust_for_weekend(loan['return_date'] + timedelta(days=7))
            loan['extended'], loan['reminded'] = True, False 
            save_data()
            await query.edit_message_text(f"✅ تم التمديد.\nالموعد الجديد: {format_date(loan['return_date'])}")

    elif data == "req_ret":
        loan = ACTIVE_LOANS.get(user_id)
        if loan:
            kb = [[InlineKeyboardButton("✅ تأكيد الاستلام", callback_data=f"conf_{user_id}")]]
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"📥 **طلب إرجاع:** {loan['name']}\n📖 {loan['book']}", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
            await query.edit_message_text("⏳ تم إرسال الطلب للمكتبة.")

    elif data.startswith("conf_"):
        uid = int(data.split("_")[1])
        if uid in ACTIVE_LOANS:
            BORROWED_BOOKS.discard(ACTIVE_LOANS[uid]['book'])
            del ACTIVE_LOANS[uid]
            save_data()
            await query.edit_message_text("✅ تم التأكيد.")
            try: await context.bot.send_message(chat_id=uid, text="✨ تم تأكيد الإرجاع، شكراً لك!")
            except: pass

    elif data == "back_to_cats":
        kb = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in LIBRARY_DATA.keys()]
        await query.edit_message_text("اختر القسم:", reply_markup=InlineKeyboardMarkup(kb))

# --- 6. التشغيل النهائي ---
def main():
    load_data()
    threading.Thread(target=run_flask, daemon=True).start()
    
    # حل مشكلة NoneType object has no attribute 'run_repeating'
    application = Application.builder().token(TOKEN).build()
    
    if application.job_queue:
        application.job_queue.run_repeating(reminder_job, interval=3600, first=10)
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__': main()
            
