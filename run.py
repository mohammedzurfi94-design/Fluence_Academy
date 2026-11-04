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
import os
from app.bot.bot_instance import create_bot, create_dispatcher
from app.dashboard.admin_app import admin_app

async def start_web_dashboard():
    """Starts the FastAPI Admin Portal compatible with Render and Localhost."""
    listen_port = int(os.environ.get("PORT", settings.PORT or settings.ADMIN_PORT or 8000))
    listen_host = "0.0.0.0"

    print(f"🌐 Admin Dashboard listening on : {listen_host}:{listen_port}")
    config = uvicorn.Config(
        app=admin_app,
        host=listen_host,
        port=listen_port,
        log_level="info"
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

async def init_and_run_bot():
    """Initializes database and runs Telegram Bot concurrently with web dashboard."""
    try:
        print("\n[Step 1/2] Initializing Database & Verifying Tables...")
        await init_database()
        print("✅ Database verified and ready.")
    except Exception as e:
        print(f"⚠️ Warning: Database initialization warning: {e}")

    if not settings.TELEGRAM_BOT_TOKEN or "YOUR_" in settings.TELEGRAM_BOT_TOKEN:
        print("\n⚠️ Telegram Bot Token is not configured. Bot will not start.")
        return

    print(f"\n[Step 2/2] Launching Telegram Bot...")
    print(f"📢 Channel Gateway : {settings.REQUIRED_TELEGRAM_CHANNEL}")
    await start_telegram_bot()

async def main():
    print("=" * 65)
    print("🎓 FLUENCE ACADEMY SYSTEM - UNIFIED SERVER (CLOUD READY)")
    print("=" * 65)

    listen_port = int(os.environ.get("PORT", settings.PORT or settings.ADMIN_PORT or 8000))
    listen_host = "0.0.0.0"
    print(f"🌐 Binding Web Port Immediately to: {listen_host}:{listen_port}")
    print(f"👤 Admin Username                : {settings.DEFAULT_ADMIN_USERNAME}")
    print(f"🔑 Admin Password                : {settings.DEFAULT_ADMIN_PASSWORD}")
    print("=" * 65 + "\n")

    # Run Web Server immediately so Render port scanning passes instantly,
    # while DB verification and Telegram bot launch concurrently.
    await asyncio.gather(
        start_web_dashboard(),
        init_and_run_bot()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Fluence Academy System stopped safely. Goodbye!")
