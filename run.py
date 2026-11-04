import asyncio
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import uvicorn
from app.core.config import settings
from app.database.init_db import init_database
from app.bot.bot_instance import create_bot, create_dispatcher
from app.dashboard.admin_app import admin_app

async def start_web_dashboard():
    """Starts the FastAPI Admin Portal on localhost."""
    config = uvicorn.Config(
        app=admin_app,
        host=settings.ADMIN_HOST,
        port=settings.ADMIN_PORT,
        log_level="warning"
    )
    server = uvicorn.Server(config)
    await server.serve()

async def start_telegram_bot():
    """Starts the aiogram Telegram Educational Bot with automatic reconnection."""
    while True:
        bot = create_bot()
        dp = create_dispatcher()
        try:
            bot_info = await bot.get_me()
            print(f"🤖 Telegram Bot connected as: @{bot_info.username}")
            await dp.start_polling(bot, handle_signals=False)
        except Exception as e:
            print(f"[Bot Notice] Polling paused: {e}. Reconnecting automatically in 5s...")
            await asyncio.sleep(5)
        finally:
            try:
                await bot.session.close()
            except Exception:
                pass

async def main():
    print("=" * 65)
    print("🎓 FLUENCE ACADEMY SYSTEM - UNIFIED SERVER")
    print("=" * 65)

    # 1. Initialize Database Tables and Default Content
    print("\n[Step 1/3] Initializing Database & Verifying Tables...")
    await init_database()

    # 2. Check bot token
    if not settings.TELEGRAM_BOT_TOKEN or "YOUR_" in settings.TELEGRAM_BOT_TOKEN:
        print("\n⚠️ Telegram Bot Token is not set in .env. Bot will not start.")
        return

    # 3. Print access information
    print("\n[Step 2/3] Launching Web Admin Dashboard...")
    print(f"🌐 Admin Dashboard URL : http://{settings.ADMIN_HOST}:{settings.ADMIN_PORT}")
    print(f"👤 Username            : {settings.DEFAULT_ADMIN_USERNAME}")
    print(f"🔑 Password            : {settings.DEFAULT_ADMIN_PASSWORD}")

    print("\n[Step 3/3] Launching Telegram Bot...")
    print(f"📢 Channel Gateway     : {settings.REQUIRED_TELEGRAM_CHANNEL}")
    print("\n🚀 Both the Web Dashboard and Telegram Bot are now running concurrently!")
    print("   Press Ctrl+C at any time to shut down the server safely.")
    print("=" * 65 + "\n")

    # Run both services simultaneously
    await asyncio.gather(
        start_web_dashboard(),
        start_telegram_bot()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Fluence Academy System stopped safely. Goodbye!")
