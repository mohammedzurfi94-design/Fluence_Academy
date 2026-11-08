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
    clean_text_for_tts,
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
    Guarantees 100% delivery without crashing on entity parse errors.
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
    Runs asynchronously with a 3.5s timeout so it never blocks the conversation.
    """
    storage_dir = "storage"
    os.makedirs(storage_dir, exist_ok=True)
    user_id = message.from_user.id if message.from_user else message.chat.id
    temp_tts_path = os.path.join(storage_dir, f"bot_reply_{user_id}_{message.message_id}.mp3")

    try:
        short_text = clean_text_for_tts(text_to_speak)
        sentences = re.split(r'(?<=[.!?])\s+', short_text)
        sample = sentences[0] if sentences else short_text[:120]
        if len(sample) > 140:
            sample = sample[:140]

        await asyncio.wait_for(
            asyncio.to_thread(text_to_speech_gtts, sample, temp_tts_path),
            timeout=3.5
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

@ai_router.message(StateFilter("*"), F.text.contains("المساعد اللغوي") | F.text.contains("AI Tutor"))
@ai_router.message(StateFilter("*"), Command("ai", "tutor", "aitutor"))
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

@ai_router.callback_query(StateFilter("*"), F.data == "start_ai_tutor_chat")
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
    print(f"[AI Tutor LOG] User @{message.from_user.username} exited AI Tutor mode.", flush=True)
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
    Delivers text responses immediately and handles TTS pronunciation asynchronously.
    """
    print(f"\n[AI Tutor LOG] Received message from @{message.from_user.username} (ID: {message.from_user.id})", flush=True)

    # 1. Handle Voice & Audio
    if message.voice or message.audio:
        file_obj = message.voice or message.audio
        print(f"[AI Tutor LOG] 🎙️ Processing Audio/Voice message (file_id: {file_obj.file_id})...", flush=True)

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
            print(f"[AI Tutor LOG] Transcribed text: '{transcribed_text}'", flush=True)

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
            print(f"[AI Tutor LOG] AI response generated: '{ai_reply[:80]}...'", flush=True)

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

            # Send audio pronunciation asynchronously in background
            asyncio.create_task(send_tts_voice_response(message, ai_reply))

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
        print(f"[AI Tutor LOG] ✍️ Processing Text message: '{user_text}'", flush=True)

        try:
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        except Exception:
            pass

        data = await state.get_data()
        history = data.get("history", [])

        ai_reply = await asyncio.to_thread(chat_with_ai_tutor, user_text, history)
        print(f"[AI Tutor LOG] AI response generated: '{ai_reply[:80]}...'", flush=True)

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

        # Send audio pronunciation asynchronously in background
        asyncio.create_task(send_tts_voice_response(message, ai_reply))
        print("[AI Tutor LOG] Text interaction finished successfully!", flush=True)

# =========================================================================
# Academic Writing Reviewer (University Professor Engine)
# =========================================================================

@ai_router.message(StateFilter("*"), F.text.contains("مصحح الكتابة الأكاديمية") | F.text.contains("Academic Writing"))
@ai_router.message(StateFilter("*"), Command("academic", "writing"))
async def handle_start_academic_writing(message: Message, state: FSMContext):
    """Activates Academic Writing Reviewer mode (isolated state)."""
    await state.clear()
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

@ai_router.callback_query(StateFilter("*"), F.data == "start_academic_reviewer_chat")
async def handle_start_academic_writing_callback(callback: CallbackQuery, state: FSMContext):
    """Callback launcher for Academic Writing Reviewer from inline menu."""
    await callback.answer()
    if callback.message:
        await handle_start_academic_writing(callback.message, state)

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
    """Processes university student academic writing submission."""
    student_text = (message.text or "").strip()
    print(f"[Academic Review LOG] Received academic text ({len(student_text)} chars) from @{message.from_user.username}", flush=True)

    if len(student_text.split()) < 5:
        await message.answer(
            "⚠️ <b>النص قصير جداً للتدقيق الأكاديمي!</b>\n\n"
            "يرجى إرسال فقرة أو مقال يتكون من 15 كلمة على الأقل ليتمكن الأستاذ الجامعي من تقييم البنية والمفردات والأسلوب الأكاديمي.",
            reply_markup=get_academic_writing_keyboard(),
            parse_mode="HTML"
        )
        return

    await message.answer(
        "🧐 <b>جاري فحص وتدقيق النص الأكاديمي بواسطة بروفيسور الأكاديمية...</b>\n"
        "<i>يتم فحص المفردات الرسمية، أدوات الربط، النحو، والأسلوب الأكاديمي...</i>",
        parse_mode="HTML"
    )

    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except Exception:
        pass

    try:
        review_result = await asyncio.to_thread(review_academic_writing, student_text)
        print(f"[Academic Review LOG] Academic review successfully completed for @{message.from_user.username}", flush=True)

        safe_review = format_ai_text_for_telegram(review_result)
        response_card = (
            "🏛️ <b>تقرير التقييم والتدقيق الأكاديمي (Academic Review Report)</b>\n"
            "═" * 32 + "\n\n"
            f"{safe_review}\n\n"
            "═" * 32 + "\n"
            "✍️ <i>يمكنك إرسال مقال أو فقرة أخرى للتدقيق، أو الضغط على «🔙 العودة للقائمة الرئيسية».</i>"
        )

        await send_safe_message(message, response_card, reply_markup=get_academic_writing_keyboard())

    except Exception as e:
        print(f"[Academic Review ERROR] {e}", flush=True)
        logger.error(f"[Academic Review Error] {e}", exc_info=True)
        await message.answer(
            "⚠️ <b>عذراً، حدث خطأ أثناء التدقيق الأكاديمي.</b>\n\n"
            "يرجى تجربة إرسال النص مجدداً أو تقسيمه إلى أجزاء أصغر.",
            reply_markup=get_academic_writing_keyboard(),
            parse_mode="HTML"
        )

# =========================================================================
# Daily English Challenge (Interactive Quizmaster Engine)
# =========================================================================

@ai_router.message(StateFilter("*"), F.text.contains("تحدي اليوم") | F.text.contains("Daily Challenge"))
@ai_router.message(StateFilter("*"), Command("challenge"))
async def handle_start_daily_challenge(message: Message, state: FSMContext):
    """Generates a new daily challenge question and waits for answer."""
    await state.clear()
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
        print(f"[Daily Challenge LOG] Question generated: '{question[:60]}...'", flush=True)

        await state.update_data(current_question=question)

        formatted_msg = (
            "🎯 <b>تحدي اليوم التفاعلي | Daily English Challenge</b>\n"
            "═" * 32 + "\n\n"
            f"{question}\n\n"
            "💬 <b>أرسل إجابتك الآن في المحادثة أدناه (مثلاً: A أو الكلمة الصحيحة)!</b>"
        )

        await send_safe_message(message, formatted_msg, reply_markup=get_daily_challenge_keyboard())

    except Exception as e:
        print(f"[Daily Challenge ERROR] {e}", flush=True)
        logger.error(f"[Daily Challenge Error] {e}", exc_info=True)
        await message.answer(
            "⚠️ <b>عذراً، حدث تأخر في توليد التحدي اليومي.</b>\n"
            "يرجى الضغط على الزر والمحاولة مرة أخرى.",
            reply_markup=get_main_reply_keyboard(),
            parse_mode="HTML"
        )
        await state.clear()

@ai_router.callback_query(StateFilter("*"), F.data == "open_daily_challenge")
async def handle_start_daily_challenge_callback(callback: CallbackQuery, state: FSMContext):
    """Callback launcher for Daily English Challenge from inline menu."""
    await callback.answer()
    await state.clear()
    if callback.message:
        await handle_start_daily_challenge(callback.message, state)

@ai_router.message(DailyChallengeStates.waiting_answer, F.text.contains("العودة للقائمة الرئيسية") | F.text.in_(["/exit", "/stop", "خروج", "Exit"]))
async def handle_exit_daily_challenge(message: Message, state: FSMContext):
    """Exits daily challenge and returns to main menu."""
    await state.clear()
    await message.answer(
        "✅ <b>تم الخروج من تحدي اليوم بنجاح.</b>\n\n"
        "اختر من القائمة أدناه لمتابعة دراستك: 👇",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="HTML"
    )

@ai_router.message(DailyChallengeStates.waiting_answer, F.text.contains("سؤال آخر") | F.text.contains("New Question"))
async def handle_new_daily_challenge_question(message: Message, state: FSMContext):
    """Requests another fresh question in daily challenge mode."""
    await handle_start_daily_challenge(message, state)

@ai_router.message(DailyChallengeStates.waiting_answer, F.text)
async def handle_evaluate_daily_challenge_answer(message: Message, state: FSMContext):
    """Evaluates student's answer to the challenge question."""
    user_answer = (message.text or "").strip()
    data = await state.get_data()
    question = data.get("current_question", "")

    if not question:
        await message.answer("⚠️ انتهت صلاحية هذا السؤال. جاري توليد سؤال جديد...")
        await handle_start_daily_challenge(message, state)
        return

    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except Exception:
        pass

    try:
        evaluation = await asyncio.to_thread(evaluate_daily_challenge, question, user_answer)
        safe_eval = format_ai_text_for_telegram(evaluation)

        eval_card = (
            "🎯 <b>نتيجة تقييم إجابتك | Answer Evaluation</b>\n"
            "═" * 32 + "\n\n"
            f"{safe_eval}\n\n"
            "═" * 32 + "\n"
            "👇 <i>اضغط «🎯 سؤال آخر» للحصول على تحدٍ جديد، أو «🔙 العودة للقائمة الرئيسية».</i>"
        )

        await send_safe_message(message, eval_card, reply_markup=get_daily_challenge_keyboard())

    except Exception as e:
        logger.error(f"[Evaluate Challenge Error] {e}", exc_info=True)
        await message.answer(
            "⚠️ <b>حدث خطأ أثناء تقييم الإجابة.</b> يرجى المحاولة مرة أخرى.",
            reply_markup=get_daily_challenge_keyboard(),
            parse_mode="HTML"
        )
