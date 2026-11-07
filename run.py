import asyncio
import sys

# Ensure UTF-8 and immediate line buffering on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
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
    listen_port = int(os.environ.get("PORT", 8080))
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
    """Starts the aiogram Telegram Educational Bot with automatic reconnection and daily scheduler."""
    from app.services.scheduler_service import start_daily_scheduler
    while True:
        bot = create_bot()
        dp = create_dispatcher()
        scheduler_task = None
        try:
            bot_info = await bot.get_me()
            print(f"🤖 Telegram Bot connected as: @{bot_info.username}", flush=True)
            scheduler_task = asyncio.create_task(start_daily_scheduler(bot))
            await dp.start_polling(bot, handle_signals=False)
        except Exception as e:
            print(f"[Bot Notice] Polling paused: {e}. Reconnecting automatically in 5s...", flush=True)
            await asyncio.sleep(5)
        finally:
            if scheduler_task and not scheduler_task.done():
                scheduler_task.cancel()
            try:
                await bot.session.close()
            except Exception:
                pass

async def init_and_run_bot():
    """Initializes database and runs Telegram Bot concurrently with web dashboard."""
    try:
        print("\n[Step 1/2] Initializing Database & Verifying Tables...", flush=True)
        await init_database()
        print("✅ Database verified and ready.", flush=True)
    except Exception as e:
        print(f"⚠️ Warning: Database initialization warning: {e}", flush=True)

    if not settings.TELEGRAM_BOT_TOKEN or "YOUR_" in settings.TELEGRAM_BOT_TOKEN:
        print("\n⚠️ Telegram Bot Token is not configured. Bot will not start.", flush=True)
        return

    print(f"\n[Step 2/2] Launching Telegram Bot...", flush=True)
    print(f"📢 Channel Gateway : {settings.REQUIRED_TELEGRAM_CHANNEL}", flush=True)
    await start_telegram_bot()

async def main():
    print("=" * 65, flush=True)
    print("🎓 FLUENCE ACADEMY SYSTEM - UNIFIED SERVER (CLOUD READY)", flush=True)
    print("=" * 65, flush=True)

    listen_port = int(os.environ.get("PORT", 8080))
    listen_host = "0.0.0.0"
    print(f"🌐 Binding Web Port Immediately to: {listen_host}:{listen_port}", flush=True)
    print(f"👤 Admin Username                : {settings.DEFAULT_ADMIN_USERNAME}", flush=True)
    print(f"🔑 Admin Password                : {settings.DEFAULT_ADMIN_PASSWORD}", flush=True)
    print("=" * 65 + "\n", flush=True)

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
        print("\n🛑 Fluence Academy System stopped safely. Goodbye!", flush=True)
    except Exception as e:
        print(f"\n❌ Server crashed with error: {e}", flush=True)
