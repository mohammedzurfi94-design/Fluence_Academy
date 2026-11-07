import os
import asyncio
import logging
import html
import re
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from app.services.ai_service import (
    chat_with_ai_tutor,
    transcribe_audio_groq,
    text_to_speech_gtts,
    review_academic_writing,
    generate_daily_challenge,
    evaluate_daily_challenge
)
from app.bot.keyboards.main_menu import (
    get_main_reply_keyboard,
    get_ai_chat_keyboard,
    get_academic_writing_keyboard,
    get_daily_challenge_keyboard
)

logger = logging.getLogger(__name__)

ai_router = Router(name="ai_router")

class AITutorStates(StatesGroup):
    chatting = State()

class AcademicWritingStates(StatesGroup):
    reviewing = State()

class DailyChallengeStates(StatesGroup):
    waiting_answer = State()

async def send_safe_message(message: Message, text: str, reply_markup=None):
    """
    Safely sends text message to Telegram:
    Cleans incompatible tags like <br>, tries HTML mode first, and falls back to plain text mode.
    Guarantees 100% delivery without crashing on entity parse errors.
    """
    # Replace <br> tags with newlines
    clean_text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    try:
        await message.answer(clean_text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as parse_err:
        print(f"[Telegram Send Notice] HTML parsing failed ({parse_err}), falling back to plain text.", flush=True)
        plain_text = re.sub(r"<[^>]+>", "", clean_text)
        plain_text = html.unescape(plain_text)
        await message.answer(plain_text, reply_markup=reply_markup, parse_mode=None)

async def send_tts_voice_response(message: Message, text_to_speak: str):
    """
    Converts English tutor response into speech using gTTS (British Accent),
    sends it as a voice note to the student, and safely removes the temp file.
    """
    storage_dir = "storage"
    os.makedirs(storage_dir, exist_ok=True)
    temp_tts_path = os.path.join(storage_dir, f"bot_reply_{message.from_user.id}_{message.message_id}.mp3")

    try:
        try:
            await message.bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
        except Exception:
            pass

        await asyncio.to_thread(text_to_speech_gtts, text_to_speak, temp_tts_path)

        if os.path.exists(temp_tts_path) and os.path.getsize(temp_tts_path) > 0:
            voice_file = FSInputFile(temp_tts_path)
            await message.answer_voice(
                voice=voice_file,
                caption="🎙️ <i>استمع إلى النطق واللفظ النموذجي (British English)</i>",
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"[TTS Voice Warning] Could not send voice note: {e}", flush=True)
        logger.warning(f"[TTS Voice Warning] {e}")
    finally:
        if os.path.exists(temp_tts_path):
            try:
                os.remove(temp_tts_path)
            except Exception:
                pass

# =========================================================================
# AI English Tutor Handlers
# =========================================================================

@ai_router.message(F.text.contains("المساعد اللغوي") | F.text.contains("AI Tutor") | Command("ai_mode"))
async def handle_start_ai_tutor(message: Message, state: FSMContext):
    """Starts interactive AI English Tutor mode."""
    await state.set_state(AITutorStates.chatting)
    print(f"[AI Tutor LOG] User @{message.from_user.username} entered AI Tutor mode.", flush=True)

    welcome_text = (
        "🤖 <b>أهلاً بك في قسم المساعد اللغوي الذكي! (Fluence AI Tutor)</b>\n\n"
        "أنا معلمك الخاص للغة الإنجليزية من <b>أكاديمية فلوينس</b> 🎓\n"
        "يسعدني مساعدتك في:\n"
        "• 🗣️ <b>المحادثة بالإنجليزية</b> وتصحيح الأخطاء اللغوية فورياً.\n"
        "• 🎙️ <b>التدرب على النطق واللفظ:</b> أرسل رسالة صوتية (Voice Note) وسأستمع إليها وأرد عليك بنص وتسجيل صوتي باللكنة البريطانية.\n"
        "• 📖 <b>شرح القواعد والمفردات</b> وتجهيزك لاختبارات IELTS / TOEFL.\n\n"
        "✍️ <i>تفضل بإرسال سؤالك الآن كنص أو رسالة صوتية!</i>\n"
        "🚪 <i>للخروج في أي وقت، اضغط على زر</i> <b>«🔙 إنهاء المحادثة»</b>."
    )
    await message.answer(
        welcome_text,
        reply_markup=get_ai_chat_keyboard(),
        parse_mode="HTML"
    )

@ai_router.message(AITutorStates.chatting, F.text.contains("إنهاء المحادثة") | F.text.in_(["/exit", "/stop", "خروج", "Exit"]))
async def handle_exit_ai_tutor(message: Message, state: FSMContext):
    """Exits AI Tutor mode and returns to main menu."""
    print(f"[AI Tutor LOG] User @{message.from_user.username} exited AI Tutor mode.", flush=True)
    await state.clear()
    await message.answer(
        "✅ <b>تم إنهاء جلسة المساعد اللغوي بنجاح.</b>\n\n"
        "أحسنت صنعاً في تدريب لغتك اليوم! 🌟\n"
        "يمكنك دائماً العودة للتحدث معي من القائمة الرئيسية.",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="HTML"
    )

@ai_router.message(AITutorStates.chatting, F.text | F.voice | F.audio)
async def handle_ai_chat_message(message: Message, state: FSMContext):
    """Handles both Text and Voice/Audio messages in AI Tutor mode."""

    # 1. Handle Voice / Audio Notes
    if message.voice or message.audio:
        print(f"[AI Tutor LOG] 🎙️ Processing Voice/Audio message from @{message.from_user.username}...", flush=True)

        status_msg = await message.answer(
            "🎧 <b>مرحباً! لقد استلمت رسالتك الصوتية</b>\n"
            "<i>جاري الاستماع والتحليل بالذكاء الاصطناعي...</i>",
            parse_mode="HTML"
        )

        storage_dir = "storage"
        os.makedirs(storage_dir, exist_ok=True)
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        temp_file_path = os.path.join(storage_dir, f"voice_{message.from_user.id}_{message.message_id}.ogg")

        try:
            bot = message.bot
            file = await bot.get_file(file_id)
            await bot.download_file(file.file_path, destination=temp_file_path)
            print(f"[AI Tutor LOG] Voice downloaded to {temp_file_path}.", flush=True)

            transcribed_text = await asyncio.to_thread(transcribe_audio_groq, temp_file_path)
            print(f"[AI Tutor LOG] Whisper Transcribed: '{transcribed_text}'", flush=True)

            try:
                await status_msg.delete()
            except Exception:
                pass

            if not transcribed_text:
                await message.answer(
                    "🎙️ <b>لم يتم التعرف على صوت أو كلمات واضحة في الرسالة الصوتية.</b>\n\n"
                    "يرجى التحدث بوضوح باللغة الإنجليزية والمحاولة مرة أخرى. ✨",
                    reply_markup=get_ai_chat_keyboard(),
                    parse_mode="HTML"
                )
                return

            data = await state.get_data()
            history = data.get("history", [])

            ai_reply = await asyncio.to_thread(chat_with_ai_tutor, transcribed_text, history)

            history.append({"role": "user", "text": transcribed_text})
            history.append({"role": "model", "text": ai_reply})
            if len(history) > 20:
                history = history[-20:]
            await state.update_data(history=history)

            safe_transcribed = html.escape(transcribed_text)
            safe_ai_reply = html.escape(ai_reply)
            formatted_response = (
                f"🗣️ <b>ما سمعته منك:</b>\n"
                f"<i>«{safe_transcribed}»</i>\n\n"
                f"🤖 <b>رد المساعد اللغوي:</b>\n"
                f"{safe_ai_reply}"
            )

            await send_safe_message(
                message,
                formatted_response,
                reply_markup=get_ai_chat_keyboard()
            )

            await send_tts_voice_response(message, ai_reply)

        except Exception as e:
            print(f"[AI Tutor ERROR] Failed to process voice note: {e}", flush=True)
            logger.error(f"[Voice Handler Error] {e}", exc_info=True)
            await message.answer(
                "⚠️ <b>عذراً، حدث خطأ أثناء معالجة الرسالة الصوتية.</b>\n\n"
                "يرجى التأكد من وضوح التسجيل أو إرسال سؤالك كنص بدلاً من ذلك.",
                reply_markup=get_ai_chat_keyboard(),
                parse_mode="HTML"
            )
        finally:
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception:
                    pass

    # 2. Handle Text
    elif message.text:
        user_text = message.text.strip()
        try:
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        except Exception:
            pass

        data = await state.get_data()
        history = data.get("history", [])

        ai_reply = await asyncio.to_thread(chat_with_ai_tutor, user_text, history)

        history.append({"role": "user", "text": user_text})
        history.append({"role": "model", "text": ai_reply})
        if len(history) > 20:
            history = history[-20:]
        await state.update_data(history=history)

        safe_reply = html.escape(ai_reply)
        await send_safe_message(
            message,
            safe_reply,
            reply_markup=get_ai_chat_keyboard()
        )
        await send_tts_voice_response(message, ai_reply)

# =========================================================================
# Academic Writing Reviewer
# =========================================================================

@ai_router.message(F.text.contains("مصحح الكتابة الأكاديمية") | F.text.contains("Academic Writing"))
async def handle_start_academic_writing(message: Message, state: FSMContext):
    """Activates Academic Writing Reviewer mode (isolated state)."""
    await state.set_state(AcademicWritingStates.reviewing)
    print(f"[Academic Review LOG] User @{message.from_user.username} entered Academic Writing mode.", flush=True)

    welcome_text = (
        "🏛️ <b>مرحباً بك في قسم مصحح الكتابة الأكاديمية!</b> ✍️📜\n\n"
        "هنا يتولى الذكاء الاصطناعي دور <b>أستاذ جامعي متخصص في اللغة الإنجليزية وآدابها</b> لتقييم وتدقيق أبحاثك ومقالاتك الأكاديمية وتحليلاتك الأدبية.\n\n"
        "🎯 <b>معايير التقييم الصارمة:</b>\n"
        "• <b>Academic Tone & Vocabulary:</b> استخدام المفردات الأكاديمية الرصينة.\n"
        "• <b>Coherence & Transitions:</b> قوة أدوات الربط والتماسك الفكري بين الفقرات.\n"
        "• <b>Grammar & Variety:</b> الدقة النحوية وتنوع التراكيب اللغوية المعقدة.\n"
        "• <b>Literature Analysis:</b> تحليل النصوص الأدبية في الشعر والمسرح والرواية العالمية.\n\n"
        "📝 <b>كيف تبدأ؟</b>\n"
        "أرسل مقالك أو فقرتك الأكاديمية في رسالة أدناه، وسأقدم لك تقييماً شاملاً مع نسخة أكاديمية مصقولة واحترافية!\n\n"
        "🚪 <i>للعودة في أي وقت، اضغط على زر</i> <b>«🔙 العودة للقائمة الرئيسية»</b>."
    )
    await message.answer(
        welcome_text,
        reply_markup=get_academic_writing_keyboard(),
        parse_mode="HTML"
    )

@ai_router.message(AcademicWritingStates.reviewing, F.text.contains("العودة للقائمة الرئيسية") | F.text.contains("إنهاء") | F.text.in_(["/exit", "/stop", "خروج", "Exit"]))
async def handle_exit_academic_writing(message: Message, state: FSMContext):
    """Exits Academic Writing mode and restores main menu."""
    print(f"[Academic Review LOG] User @{message.from_user.username} exited Academic Writing mode.", flush=True)
    await state.clear()
    exit_text = (
        "✅ <b>تم الخروج من قسم مصحح الكتابة الأكاديمية بنجاح.</b>\n\n"
        "نتمنى لك دوام التوفيق والتميز في مسيرتك العلمية والأكاديمية! 🎓🌟\n\n"
        "اختر من القائمة أدناه للوصول إلى باقي أقسام الأكاديمية: 👇"
    )
    await message.answer(
        exit_text,
        reply_markup=get_main_reply_keyboard(),
        parse_mode="HTML"
    )

@ai_router.message(AcademicWritingStates.reviewing, F.text)
async def handle_process_academic_text(message: Message, state: FSMContext):
    """Processes student academic essay through Groq's University Professor model."""
    student_text = message.text.strip()
    if not student_text:
        return

    print(f"[Academic Review LOG] Evaluating essay ({len(student_text)} chars) for @{message.from_user.username}...", flush=True)

    await message.answer(
        "🔍 <b>جاري قراءة وتحليل النص الأكاديمي بواسطة البروفيسور الذكي...</b>\n"
        "<i>يتم التدقيق في الأسلوب، أدوات الربط، القواعد، وصياغة نسخة مصقولة. يرجى الانتظار ثوانٍ معدودة...</i>",
        parse_mode="HTML"
    )

    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except Exception:
        pass

    try:
        review_result = await asyncio.to_thread(review_academic_writing, student_text)
        print(f"[Academic Review LOG] Academic review generated successfully ({len(review_result)} chars).", flush=True)

        header = "🎓 <b>تقرير التقييم والتدقيق الأكاديمي:</b>\n" + "═" * 32 + "\n\n"
        safe_review = html.escape(review_result)
        full_message = header + safe_review

        if len(full_message) <= 3900:
            await send_safe_message(
                message,
                full_message,
                reply_markup=get_academic_writing_keyboard()
            )
        else:
            chunks = [full_message[i:i+3800] for i in range(0, len(full_message), 3800)]
            for idx, chunk in enumerate(chunks):
                is_last = (idx == len(chunks) - 1)
                await send_safe_message(
                    message,
                    chunk,
                    reply_markup=get_academic_writing_keyboard() if is_last else None
                )

    except Exception as e:
        print(f"[Academic Review ERROR] Review failed: {e}", flush=True)
        logger.error(f"[Academic Review Error] {e}", exc_info=True)
        await message.answer(
            "⚠️ <b>عذراً، حدث خطأ أثناء تدقيق النص الأكاديمي.</b>\n\n"
            "يرجى تجربة إرسال النص مجدداً أو تقسيمه إلى أجزاء أصغر.",
            reply_markup=get_academic_writing_keyboard(),
            parse_mode="HTML"
        )

# =========================================================================
# Daily English Challenge (Interactive Quizmaster Engine)
# =========================================================================

@ai_router.message(F.text.contains("تحدي اليوم") | F.text.contains("Daily Challenge"))
async def handle_start_daily_challenge(message: Message, state: FSMContext):
    """Generates a new daily challenge question and waits for answer."""
    await state.set_state(DailyChallengeStates.waiting_answer)
    print(f"[Daily Challenge LOG] User @{message.from_user.username} requested a Daily Challenge.", flush=True)

    await message.answer(
        "🎯 <b>جاري إعداد تحدي اليوم الخاص بك من خبير الأكاديمية...</b>\n"
        "<i>ثوانٍ معدودة...</i>",
        parse_mode="HTML"
    )

    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except Exception:
        pass

    try:
        question = await asyncio.to_thread(generate_daily_challenge)
        await state.update_data(current_question=question)

        prompt_text = (
            "🎯 <b>تحدي اليوم في اللغة الإنجليزية:</b>\n"
            "═" * 32 + "\n\n"
            f"{html.escape(question)}\n\n"
            "✍️ <i>أرسل إجابتك الآن لتقييمها فورياً!</i>"
        )
        await send_safe_message(
            message,
            prompt_text,
            reply_markup=get_daily_challenge_keyboard()
        )
    except Exception as e:
        print(f"[Daily Challenge ERROR] Failed to generate challenge: {e}", flush=True)
        await message.answer(
            "⚠️ عذراً، حدث خطأ أثناء توليد سؤال التحدي. يرجى الضغط على الزر مرة أخرى للمحاولة.",
            reply_markup=get_daily_challenge_keyboard()
        )

@ai_router.message(DailyChallengeStates.waiting_answer, F.text.contains("العودة للقائمة الرئيسية") | F.text.in_(["/exit", "/stop", "خروج", "Exit"]))
async def handle_exit_daily_challenge(message: Message, state: FSMContext):
    """Exits Daily Challenge mode and restores main menu."""
    await state.clear()
    await message.answer(
        "✅ <b>تم الخروج من تحدي اليوم بنجاح.</b>\n\n"
        "ننتظرك غداً في تحدٍ جديد لتطوير مستواك! 🌟",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="HTML"
    )

@ai_router.message(DailyChallengeStates.waiting_answer, F.text.contains("سؤال آخر") | F.text.contains("New Question"))
async def handle_new_daily_challenge_question(message: Message, state: FSMContext):
    """Generates another challenge question."""
    await handle_start_daily_challenge(message, state)

@ai_router.message(DailyChallengeStates.waiting_answer, F.text)
async def handle_evaluate_daily_challenge_answer(message: Message, state: FSMContext):
    """Evaluates the student's answer and provides friendly feedback."""
    user_answer = message.text.strip()
    data = await state.get_data()
    question = data.get("current_question", "")

    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except Exception:
        pass

    try:
        evaluation = await asyncio.to_thread(evaluate_daily_challenge, question, user_answer)

        response_text = (
            "📝 <b>تقييم إجابتك على التحدي:</b>\n"
            "═" * 32 + "\n\n"
            f"{html.escape(evaluation)}\n\n"
            "💡 <i>لخوض تحدٍ آخر اضغط «🎯 سؤال آخر» أو عد للقائمة الرئيسية.</i>"
        )
        await send_safe_message(
            message,
            response_text,
            reply_markup=get_daily_challenge_keyboard()
        )
    except Exception as e:
        print(f"[Daily Challenge ERROR] Evaluation failed: {e}", flush=True)
        await message.answer(
            "⚠️ حدث خطأ أثناء تقييم إجابتك. يرجى تجربة إرسالها مجدداً.",
            reply_markup=get_daily_challenge_keyboard()
        )
