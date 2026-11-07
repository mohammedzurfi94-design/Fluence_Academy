import os
import asyncio
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from app.services.ai_service import (
    chat_with_ai_tutor,
    transcribe_audio_groq,
    text_to_speech_gtts,
    review_academic_writing
)
from app.bot.keyboards.main_menu import (
    get_main_reply_keyboard,
    get_ai_chat_keyboard,
    get_academic_writing_keyboard
)

logger = logging.getLogger(__name__)

ai_router = Router(name="ai_router")

class AITutorStates(StatesGroup):
    chatting = State()

class AcademicWritingStates(StatesGroup):
    reviewing = State()

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
        print(f"[AI Tutor TTS ERROR] {tts_err}", flush=True)
        logger.warning(f"[TTS Pronunciation Error] {tts_err}")
    finally:
        if os.path.exists(temp_tts_path):
            try:
                os.remove(temp_tts_path)
            except Exception:
                pass

@ai_router.message(F.text.contains("المساعد اللغوي") | F.text.contains("AI Tutor"))
async def handle_start_ai_tutor_chat(message: Message, state: FSMContext):
    """Activates AI English Tutor conversation mode."""
    await state.set_state(AITutorStates.chatting)
    await state.update_data(history=[])
    print(f"[AI Tutor LOG] User @{message.from_user.username} entered AI Tutor mode.", flush=True)

    welcome_text = (
        "🤖 <b>مرحباً بك في خدمة المساعد اللغوي الذكي (AI English Tutor)!</b> 🎓\n\n"
        "أنا هنا لمساعدتك على ممارسة وتطوير لغتك الإنجليزية، وتصحيح أي أخطاء قواعدية أو إملائية أو لفظية بلطف ودقة.\n\n"
        "💬 <b>كيف تبدأ؟</b>\n"
        "• اكتب أي رسالة أو جملة باللغة الإنجليزية ✍️\n"
        "• أو أرسل <b>رسالة صوتية (Voice Note) 🎙️</b> وسأستمع لنطقك وأساعدك فوراً!\n\n"
        "🎧 <b>الميزة الصوتية التفاعلية:</b>\n"
        "سأقوم بالرد عليك كتابياً، وسأرسل لك أيضاً <b>بصمة صوتية باللكنة البريطانية المعتمدة</b> لتستمع للنطق الصحيح وتكرره معي! 🌟\n\n"
        "🚪 <i>للخروج والعودة للقائمة الرئيسية في أي وقت، اضغط على زر</i> <b>«🔙 إنهاء المحادثة»</b>."
    )
    await message.answer(
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
    """Unified MessageHandler for AI English Tutor (Voice, Audio, and Text)."""
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
            print(f"[AI Tutor LOG] Downloading audio file to: {temp_file_path}", flush=True)
            await message.bot.download(file=file_obj, destination=temp_file_path)

            print("[AI Tutor LOG] Sending to Groq Whisper for transcription...", flush=True)
            transcribed_text = await asyncio.to_thread(transcribe_audio_groq, temp_file_path)
            print(f"[AI Tutor LOG] Transcription result: '{transcribed_text}'", flush=True)

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

            formatted_response = (
                f"🗣️ <b>ما سمعته منك:</b>\n"
                f"<i>«{transcribed_text}»</i>\n\n"
                f"🤖 <b>رد المساعد اللغوي:</b>\n"
                f"{ai_reply}"
            )

            await message.answer(
                formatted_response,
                reply_markup=get_ai_chat_keyboard(),
                parse_mode="HTML"
            )

            print("[AI Tutor LOG] Generating TTS voice pronunciation...", flush=True)
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
        print(f"[AI Tutor LOG] ✍️ Processing Text message: '{user_text}'", flush=True)

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

        await message.answer(
            ai_reply,
            reply_markup=get_ai_chat_keyboard()
        )

        await send_tts_voice_response(message, ai_reply)

# =========================================================================
# Academic Writing Reviewer (University Professor Engine)
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
        full_message = header + review_result

        if len(full_message) <= 4000:
            await message.answer(
                full_message,
                reply_markup=get_academic_writing_keyboard()
            )
        else:
            chunks = [full_message[i:i+3800] for i in range(0, len(full_message), 3800)]
            for idx, chunk in enumerate(chunks):
                is_last = (idx == len(chunks) - 1)
                await message.answer(
                    chunk,
                    reply_markup=get_academic_writing_keyboard() if is_last else None
                )

    except Exception as e:
        print(f"[Academic Review ERROR] Review failed: {e}", flush=True)
        logger.error(f"[Academic Review Error] {e}", exc_info=True)
        await message.answer(
            "⚠️ <b>عذراً، حدث خطأ أثناء تدقيق النص الأكاديمي.</b>\n\n"
            "قد يكون النص طويلاً جداً أو حدث تأخر مؤقت في الاتصال. يرجى تجربة إرسال النص مجدداً أو تقسيمه إلى أجزاء أصغر.",
            reply_markup=get_academic_writing_keyboard(),
            parse_mode="HTML"
        )

@ai_router.message(Command("ai"))
async def handle_ai_command(message: Message):
    question = message.text.replace("/ai", "", 1).strip() if message.text else ""

    if not question:
        help_msg = (
            "🤖 <b>Fluence Academy AI Tutor</b>\n\n"
            "Ask any question about English grammar, vocabulary, pronunciation, or lessons!\n\n"
            "<b>Usage:</b>\n"
            "Type <code>/ai</code> followed by your question, or click <b>🤖 المساعد اللغوي (AI Tutor)</b> from the main menu!"
        )
        await message.answer(help_msg, parse_mode="HTML")
        return

    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except Exception:
        pass

    response = await asyncio.to_thread(chat_with_ai_tutor, question)
    await message.answer(response)
    await send_tts_voice_response(message, response)
