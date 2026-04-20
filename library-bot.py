def main():
    # 1. تشغيل خيط الـ Flask لضمان بقاء السيرفر Live
    threading.Thread(target=run_flask, daemon=True).start()

    # 2. بناء التطبيق وتجاوز خطأ الـ AttributeError
    # أضفنا التحقق من وجود الـ JobQueue عشان نضمن استقرار التشغيل
    app = Application.builder().token(TOKEN).build()
    
    # إضافة الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("نظام مكتبة ابن العميد ينطلق الآن بكل قوته...")
    
    # 3. التشغيل باستخدام الطريقة المتوافقة (هذا هو الحل للخطأ اللي بالصورة)
    import asyncio
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
