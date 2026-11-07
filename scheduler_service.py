import os
import asyncio
import logging
from datetime import datetime, timezone
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from sqlalchemy import select

from app.database.connection import AsyncSessionLocal
from app.database.models import User
from app.services.ai_service import generate_daily_lesson_and_quiz, text_to_speech_gtts

logger = logging.getLogger(__name__)

# Cached active daily lesson
_CURRENT_DAILY_LESSON = None
_LAST_GENERATED_DATE = None

def get_today_lesson(force_refresh: bool = False) -> dict:
    """Returns today's cached lesson or generates a fresh one."""
    global _CURRENT_DAILY_LESSON, _LAST_GENERATED_DATE
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if force_refresh or _CURRENT_DAILY_LESSON is None or _LAST_GENERATED_DATE != today_str:
        try:
            _CURRENT_DAILY_LESSON = generate_daily_lesson_and_quiz()
            _LAST_GENERATED_DATE = today_str
            print(f"[Scheduler LOG] Generated fresh daily lesson: {_CURRENT_DAILY_LESSON.get('topic')}", flush=True)
        except Exception as e:
            logger.error(f"[Scheduler Error] Generating lesson failed: {e}")
            if _CURRENT_DAILY_LESSON is None:
                from app.services.ai_service import CURATED_DAILY_LESSONS
                _CURRENT_DAILY_LESSON = CURATED_DAILY_LESSONS[0]
                _LAST_GENERATED_DATE = today_str

    return _CURRENT_DAILY_LESSON

def build_daily_lesson_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for the daily lesson message."""
    keyboard = [
        [InlineKeyboardButton(text="🚀 ابدأ اختبار هذه المعلومة الآن (Quiz)", callback_data="start_daily_info_quiz")],
        [
            InlineKeyboardButton(text="🔄 معلومة واختبار آخر", callback_data="refresh_daily_lesson"),
            InlineKeyboardButton(text="🔙 قسم الاختبارات", callback_data="back_to_quizzes_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def send_daily_lesson_to_user(bot: Bot, chat_id: int, lesson_data: dict, send_voice: bool = True) -> bool:
    """Sends the formatted daily educational info, optional voice pronunciation, and quiz button."""
    try:
        topic = lesson_data.get("topic", "Daily English Tip")
        info = lesson_data.get("info", "")
        audio_text = lesson_data.get("audio_text") or info

        caption = (
            f"💡 <b>معلومة اليوم الأكاديمية (Daily English Bite)</b> 🎓\n"
            f"📌 <b>الموضوع:</b> {topic}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{info}\n\n"
            f"🎧 <i>استمع إلى التسجيل الصوتي أدناه للتدرب على النطق واللفظ الصحيح (British English).</i>\n"
            f"👇 <i>ثم اضغط على الزر أدناه لبدء اختبار الفهم لهذه المعلومة!</i>"
        )

        # 1. Send the educational text message
        await bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=build_daily_lesson_keyboard(),
            parse_mode="HTML"
        )

        # 2. Send the voice note with pronunciation if enabled
        if send_voice and audio_text:
            storage_dir = "storage"
            os.makedirs(storage_dir, exist_ok=True)
            temp_audio = os.path.join(storage_dir, f"daily_voice_{chat_id}_{int(datetime.now().timestamp())}.mp3")
            try:
                await asyncio.to_thread(text_to_speech_gtts, audio_text, temp_audio, "en", "co.uk")
                if os.path.exists(temp_audio) and os.path.getsize(temp_audio) > 0:
                    voice_file = FSInputFile(temp_audio)
                    await bot.send_voice(
                        chat_id=chat_id,
                        voice=voice_file,
                        caption=f"🗣️ <i>نطق الجملة النموذجية الخاصة بمعلومة:</i> <b>{topic}</b>",
                        parse_mode="HTML"
                    )
            except Exception as v_err:
                logger.warning(f"[Voice Send Warning for {chat_id}] {v_err}")
            finally:
                if os.path.exists(temp_audio):
                    try:
                        os.remove(temp_audio)
                    except Exception:
                        pass

        return True
    except Exception as e:
        logger.warning(f"[Daily Lesson Send Error to {chat_id}] {e}")
        return False

async def broadcast_daily_lesson(bot: Bot) -> int:
    """Broadcasts today's lesson to all registered active students in the database."""
    lesson = get_today_lesson(force_refresh=True)
    sent_count = 0

    print(f"[Scheduler LOG] Starting daily broadcast: '{lesson.get('topic')}'...", flush=True)

    async with AsyncSessionLocal() as session:
        q = select(User).where(User.telegram_id.isnot(None), User.is_active == True)
        res = await session.execute(q)
        users = res.scalars().all()

    for u in users:
        try:
            success = await send_daily_lesson_to_user(bot, u.telegram_id, lesson, send_voice=True)
            if success:
                sent_count += 1
            # Rate limit politeness
            await asyncio.sleep(0.1)
        except Exception as err:
            logger.warning(f"[Broadcast Error for user {u.telegram_id}] {err}")

    print(f"[Scheduler LOG] Broadcast completed: Sent to {sent_count}/{len(users)} students.", flush=True)
    return sent_count

async def start_daily_scheduler(bot: Bot):
    """
    Background scheduler loop that triggers daily English lesson and quiz broadcast.
    Runs continuously alongside the Telegram Bot.
    """
    print("⏰ [Daily Scheduler] Background service started successfully.", flush=True)
    # Give the bot 10 seconds to fully connect upon boot
    await asyncio.sleep(10)

    # Initial check upon startup to cache today's lesson
    try:
        get_today_lesson()
    except Exception:
        pass

    while True:
        try:
            now = datetime.now(timezone.utc)
            # Target broadcast time: 08:00 AM UTC (11:00 AM Mecca/Baghdad time)
            # Calculate seconds until next 08:00 UTC
            target_hour = 8
            if now.hour >= target_hour:
                # Next run is tomorrow at 08:00 UTC
                next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
                next_run_timestamp = next_run.timestamp() + 86400
            else:
                next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
                next_run_timestamp = next_run.timestamp()

            wait_seconds = max(60, int(next_run_timestamp - now.timestamp()))
            print(f"⏰ [Daily Scheduler] Next scheduled broadcast in {wait_seconds // 3600}h {(wait_seconds % 3600) // 60}m.", flush=True)

            # Sleep in intervals of 30 minutes to stay responsive
            while wait_seconds > 0:
                sleep_chunk = min(1800, wait_seconds)
                await asyncio.sleep(sleep_chunk)
                wait_seconds -= sleep_chunk

            # Time to broadcast!
            await broadcast_daily_lesson(bot)

        except asyncio.CancelledError:
            print("🛑 [Daily Scheduler] Cancelled.", flush=True)
            break
        except Exception as e:
            logger.error(f"[Daily Scheduler Error] {e}", exc_info=True)
            await asyncio.sleep(300)
