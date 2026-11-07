import os
import asyncio
import logging
import html
import re
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, FSInputFile
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

def format_ai_text_for_telegram(text: str) -> str:
    """Escapes HTML and formats markdown headings and bolding for clean Telegram display."""
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text

async def send_safe_message(message: Message, text: str, reply_markup=None):
    """
    Safely sends text message to Telegram:
    Tries HTML mode first. If Telegram entity parser fails, falls back to plain text mode.
    """
    try:
        await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as parse_err:
        print(f"[Telegram Send Notice] HTML parsing failed ({parse_err}), falling back to plain text.", flush=True)
        plain_text = re.sub(r"<[^>]+>", "", text)
        await message.answer(plain_text, reply_markup=reply_markup, parse_mode=None)

async def send_tts_voice_response(message: Message, text_to_speak: str):
    """
    Converts English tutor response into speech using gTTS (British Accent),
    sends it as a voice note to the student, and safely removes the temp file.
    """
    storage_dir = "storage"
    os.makedirs(storage_dir, exist_ok=True)
    user_id = message.from_user.id if message.from_user else message.chat.id
    temp_tts_path = os.path.join(storage_dir, f"bot_reply_{user_id}_{message.message_id}.mp3")

    try:
        try:
            await message.bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
        except Exception:
            pass

        # Speak concise sample (first sentence, max 150 chars) to prevent slow network / rate-limiting
        short_text = clean_text_for_tts(text_to_speak)
        sentences = re.split(r'(?<=[.!?])\s+', short_text)
        sample = sentences[0] if sentences else short_text[:120]
        if len(sample) > 150:
            sample = sample[:150]

        await asyncio.wait_for(
            asyncio.to_thread(text_to_speech_gtts, sample, temp_tts_path),
            timeout=4.0
        )

        if os.path.exists(temp_tts_path) and os.path.getsize(temp_tts_path) > 0:
            voice_input = FSInputFile(temp_tts_path)
            try:
                await message.answer_voice(
                    voice=voice_input,
                    caption="🎧 <i>استمع إلى اللفظ والتصحيح (British Accent)</i>",
                    parse_mode="HTML"
                )
            except Exception:
                await message.answer_audio(
                    audio=voice_input,
                    title="English Tutor Pronunciation",
                    performer="Fluence English Academy"
                )
    except Exception as tts_err:
        logger.warning(f"[TTS Pronunciation Notice] {tts_err}")
    finally:
        if os.path.exists(temp_tts_path):
            try:
                os.remove(temp_tts_path)
            except Exception:
                pass

def clean_text_for_tts(text: str) -> str:
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"[*_`#~]", "", clean)
    clean = re.sub(r"[^\w\s.,!?'\"-]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

@ai_router.message(StateFilter("*"), Command("ai", "tutor", "aitutor") | F.text.contains("المساعد اللغوي") | F.text.contains("AI Tutor"))
async def handle_start_ai_tutor_chat(message: Message, state: FSMContext):
    """Activates AI English Tutor conversation mode from any previous state."""
    await state.clear()
    await state.set_state(AITutorStates.chatting)
    await state.update_data(history=[])

    raw_text = (message.text or "").strip()
    if raw_text.startswith("/ai ") and len(raw_text) > 4:
        message.text = raw_text.replace("/ai ", "", 1).strip()
        await handle_ai_chat_unified(message, state)
        return

    welcome_text = (
        "🤖 <b>مرحباً بك في خدمة المساعد اللغوي الذكي (AI English Tutor)!</b> 🎓\n\n"
        "أنا هنا لمساعدتك على ممارسة وتطوير لغتك الإنجليزية، وتصحيح أي أخطاء قواعدية أو إملائية أو لفظية بلطف ودقة.\n\n"
        "💬 <b>كيف تبدأ؟</b>\n"
        "• اكتب أي رسالة أو جملة باللغة الإنجليزية ✍️\n"
        "• أو أرسل <b>رسالة صوتية (Voice Note) 🎙️</b> وسأستمع لنطقك وأساعدك فوراً!\n\n"
        "🎧 <b>الرد الصوتي المزدوج:</b>\n"
        "سأقوم بالرد عليك كتابياً، وسأرسل لك أيضاً <b>بصمة صوتية باللكنة البريطانية المعتمدة</b> لتستمع للنطق الصحيح وتكرره معي! 🌟\n\n"
        "🚪 <i>للخروج والعودة للقائمة الرئيسية في أي وقت، اضغط على زر</i> <b>«🔙 إنهاء المحادثة»</b>."
    )
    await message.answer(
        welcome_text,
        reply_markup=get_ai_chat_keyboard(),
        parse_mode="HTML"
    )

@ai_router.callback_query(F.data == "start_ai_tutor_chat")
async def handle_start_ai_tutor_chat_callback(callback: CallbackQuery, state: FSMContext):
    """Callback launcher for AI English Tutor from inline menu."""
    await callback.answer()
    await state.clear()
    await state.set_state(AITutorStates.chatting)
    await state.update_data(history=[])

    welcome_text = (
        "🤖 <b>مرحباً بك في خدمة المساعد اللغوي الذكي (AI English Tutor)!</b> 🎓\n\n"
        "أنا هنا لمساعدتك على ممارسة وتطوير لغتك الإنجليزية، وتصحيح أي أخطاء قواعدية أو إملائية أو لفظية بلطف ودقة.\n\n"
        "💬 <b>كيف تبدأ؟</b>\n"
        "• اكتب أي رسالة أو جملة باللغة الإنجليزية ✍️\n"
        "• أو أرسل <b>رسالة صوتية (Voice Note) 🎙️</b> وسأستمع لنطقك وأساعدك فوراً!\n\n"
        "🎧 <b>الرد الصوتي المزدوج:</b>\n"
        "سأقوم بالرد عليك كتابياً، وسأرسل لك أيضاً <b>بصمة صوتية باللكنة البريطانية المعتمدة</b> لتستمع للنطق الصحيح وتكرره معي! 🌟\n\n"
        "🚪 <i>للخروج والعودة للقائمة الرئيسية في أي وقت، اضغط على زر</i> <b>«🔙 إنهاء المحادثة»</b>."
    )
    try:
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=welcome_text,
            reply_markup=get_ai_chat_keyboard(),
            parse_mode="HTML"
        )
    except Exception:
        if callback.message:
            await callback.message.answer(
                welcome_text,
                reply_markup=get_ai_chat_keyboard(),
                parse_mode="HTML"
            )

@ai_router.message(AITutorStates.chatting, F.text.contains("إنهاء المحادثة") | F.text.in_(["/exit", "/stop", "خروج", "Exit"]))
async def handle_exit_ai_tutor_chat(message: Message, state: FSMContext):
    """Exits AI Tutor conversation mode and restores main menu."""
    await state.clear()
    exit_text = (
        "✅ <b>تم إنهاء المحادثة مع المساعد اللغوي بنجاح.</b>\n\n"
        "أحسنت في ممارسة لغتك اليوم! تذكر دائماً أن الاستمرار والممارسة هما سر الإتقان. 🌟\n\n"
        "اختر من القائمة أدناه للوصول إلى باقي أقسام الأكاديمية: 👇"
    )
    await message.answer(
        exit_text,
        reply_markup=get_main_reply_keyboard(),
        parse_mode="HTML"
    )

@ai_router.message(AITutorStates.chatting, F.text | F.voice | F.audio)
async def handle_ai_chat_unified(message: Message, state: FSMContext):
    """
    Unified MessageHandler for AI English Tutor (Voice, Audio, and Text).
    """
    if message.voice or message.audio:
        file_obj = message.voice or message.audio
        await message.answer("مرحباً! لقد استلمت رسالتك الصوتية 🎧، جاري الاستماع والتحليل...")

        try:
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        except Exception:
            pass

        storage_dir = "storage"
        os.makedirs(storage_dir, exist_ok=True)
        ext = "ogg" if message.voice else (file_obj.file_name.split(".")[-1] if file_obj.file_name and "." in file_obj.file_name else "ogg")
        temp_file_path = os.path.join(storage_dir, f"temp_voice_{message.from_user.id}_{message.message_id}.{ext}")

        try:
            await message.bot.download(file=file_obj, destination=temp_file_path)
            transcribed_text = await asyncio.to_thread(transcribe_audio_groq, temp_file_path)

            if not transcribed_text or not transcribed_text.strip():
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
            safe_ai_reply = format_ai_text_for_telegram(ai_reply)
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

        safe_reply = format_ai_text_for_telegram(ai_reply)
        await send_safe_message(
            message,
            safe_reply,
            reply_markup=get_ai_chat_keyboard()
        )

        await send_tts_voice_response(message, ai_reply)

# =========================================================================
# Academic Writing Reviewer (University Professor Engine)
# =========================================================================

@ai_router.message(F.text.contains("مصحح الكتابة الأكاديمية") | F.text.contains("Academic Writing"))
async def handle_start_academic_reviewer(message: Message, state: FSMContext):
    await state.set_state(AcademicWritingStates.reviewing)
    prompt_text = (
        "✍️ <b>مرحباً بك في خدمة مصحح الكتابة الأكاديمية (Academic Writing Reviewer)!</b> 🎓\n\n"
        "هذه الخدمة مخصصة لطلبة الدراسات العليا والجامعات لتدقيق أبحاثهم ومقالاتهم الأكاديمية.\n\n"
        "📌 <b>أرسل الآن مقالك أو نصك الأكاديمي</b> (سواء باللغة الإنجليزية مباشرة أو نصاً أدبياً)، "
        "وسأقوم بتحليله وتصحيح القواعد وتزويدك بنسخة أكاديمية مصقولة وتقرير تقييم شامل من 10 درجات! ✨\n\n"
        "🚪 <i>للخروج والعودة للقائمة الرئيسية، اضغط على زر</i> <b>«🔙 العودة للقائمة الرئيسية»</b>."
    )
    await message.answer(
        prompt_text,
        reply_markup=get_academic_writing_keyboard(),
        parse_mode="HTML"
    )

@ai_router.callback_query(F.data == "start_academic_reviewer_chat")
async def handle_start_academic_reviewer_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.message:
        await handle_start_academic_reviewer(callback.message, state)

@ai_router.message(AcademicWritingStates.reviewing, F.text.contains("العودة للقائمة الرئيسية") | F.text.contains("إنهاء") | F.text.in_(["/exit", "/stop", "خروج", "Exit"]))
async def handle_exit_academic_reviewer(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "✅ تم إنهاء جلسة التدقيق الأكاديمي والعودة للقائمة الرئيسية.",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="HTML"
    )

@ai_router.message(AcademicWritingStates.reviewing, F.text)
async def handle_process_academic_text(message: Message, state: FSMContext):
    student_text = message.text.strip()
    if not student_text:
        return

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
        header = "🎓 <b>تقرير التقييم والتدقيق الأكاديمي:</b>\n" + "═" * 32 + "\n\n"
        safe_review = format_ai_text_for_telegram(review_result)
        full_message = header + safe_review

        if len(full_message) <= 3900:
            await send_safe_message(
                message,
                full_message,
                reply_markup=get_academic_writing_keyboard()
            )
        else:
            chunks = [full_message[i:i+3800] for i in range(0, len(full_message), 3800)]
            for chunk in chunks:
                await send_safe_message(message, chunk)
            await message.answer("👆 اكتمل التقرير.", reply_markup=get_academic_writing_keyboard())

    except Exception as e:
        logger.error(f"[Academic Review Error] {e}", exc_info=True)
        await message.answer(
            "⚠️ عذراً، حدث خطأ أثناء تدقيق النص الأكاديمي. يرجى المحاولة مرة أخرى لاحقاً.",
            reply_markup=get_academic_writing_keyboard()
        )

# =========================================================================
# Daily AI Challenge Engine
# =========================================================================

@ai_router.message(F.text.contains("تحدي اليوم") | F.text.contains("Daily Challenge"))
async def handle_start_daily_challenge(message: Message, state: FSMContext):
    await state.set_state(DailyChallengeStates.waiting_answer)
    await message.answer(
        "🎯 <b>جاري إعداد سؤال التحدي الذكي لليوم...</b> ⏳",
        parse_mode="HTML"
    )

    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except Exception:
        pass

    try:
        challenge_q = await asyncio.to_thread(generate_daily_challenge)
        await state.update_data(current_challenge=challenge_q)

        prompt = (
            "🎯 <b>تحدي اليوم الذكي (Daily English Challenge)</b> 🌟\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{format_ai_text_for_telegram(challenge_q)}\n\n"
            "✍️ <i>أرسل إجابتك هنا في الشات (مثلاً: A أو الكلمة المطلوبة) لمعرفة تقييمك الفوري!</i>"
        )
        await send_safe_message(
            message,
            prompt,
            reply_markup=get_daily_challenge_keyboard()
        )
    except Exception as e:
        logger.error(f"[Daily Challenge Gen Error] {e}")
        fallback_q = "Choose the correct preposition: 'She has been living in London _____ 2019.'\nA) for\nB) since\nC) in\nD) during"
        await state.update_data(current_challenge=fallback_q)
        await message.answer(
            f"🎯 <b>تحدي اليوم (Daily Challenge):</b>\n\n{fallback_q}\n\nاكتب إجابتك هنا:",
            reply_markup=get_daily_challenge_keyboard()
        )

@ai_router.callback_query(F.data == "open_daily_challenge")
async def handle_open_daily_challenge_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.message:
        await handle_start_daily_challenge(callback.message, state)

@ai_router.message(DailyChallengeStates.waiting_answer, F.text.contains("العودة للقائمة الرئيسية") | F.text.in_(["/exit", "/stop", "خروج", "Exit"]))
async def handle_exit_daily_challenge(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "✅ تم إنهاء التحدي اليومي والعودة للقائمة الرئيسية.",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="HTML"
    )

@ai_router.message(DailyChallengeStates.waiting_answer, F.text.contains("سؤال آخر") | F.text.contains("New Question"))
async def handle_new_daily_challenge_question(message: Message, state: FSMContext):
    await handle_start_daily_challenge(message, state)

@ai_router.message(DailyChallengeStates.waiting_answer, F.text)
async def handle_evaluate_student_challenge_answer(message: Message, state: FSMContext):
    user_answer = message.text.strip()
    data = await state.get_data()
    question = data.get("current_challenge", "English grammar challenge")

    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except Exception:
        pass

    try:
        evaluation = await asyncio.to_thread(evaluate_daily_challenge, question, user_answer)
        result_text = (
            "📊 <b>نتيجة تقييم إجابتك:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{format_ai_text_for_telegram(evaluation)}\n\n"
            "🎯 <i>اضغط على</i> <b>«🎯 سؤال آخر»</b> <i>لتحدٍ جديد، أو</i> <b>«🔙 العودة للقائمة الرئيسية»</b>."
        )
        await send_safe_message(
            message,
            result_text,
            reply_markup=get_daily_challenge_keyboard()
        )
    except Exception as e:
        logger.error(f"[Evaluate Challenge Error] {e}")
        await message.answer(
            f"✅ أحسنت المحاولة! إجابتك: <b>{html.escape(user_answer)}</b>.\nاضغط 'سؤال آخر' للمتابعة.",
            reply_markup=get_daily_challenge_keyboard(),
            parse_mode="HTML"
        )
