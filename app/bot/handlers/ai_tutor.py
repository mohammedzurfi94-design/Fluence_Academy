import os
import asyncio
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from app.services.ai_service import chat_with_ai_tutor, transcribe_audio_groq, text_to_speech_gtts
from app.bot.keyboards.main_menu import get_main_reply_keyboard, get_ai_chat_keyboard

logger = logging.getLogger(__name__)

ai_router = Router(name="ai_router")

class AITutorStates(StatesGroup):
    chatting = State()

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

@ai_router.message(AITutorStates.chatting, F.voice | F.audio)
async def handle_ai_voice_message(message: Message, state: FSMContext):
    """
    Downloads voice note or audio, transcribes it via Groq Whisper (whisper-large-v3),
    processes it with AI Tutor, responds with transcribed text + feedback,
    and sends a TTS voice response with correct pronunciation.
    """
    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except Exception:
        pass

    file_obj = message.voice or message.audio
    if not file_obj:
        return

    storage_dir = "storage"
    os.makedirs(storage_dir, exist_ok=True)
    ext = "ogg" if message.voice else (file_obj.file_name.split(".")[-1] if file_obj.file_name and "." in file_obj.file_name else "ogg")
    temp_file_path = os.path.join(storage_dir, f"temp_voice_{message.from_user.id}_{message.message_id}.{ext}")

    try:
        # 1. Download voice file from Telegram
        await message.bot.download(file=file_obj, destination=temp_file_path)

        # 2. Transcribe audio with Groq Whisper in background thread
        transcribed_text = await asyncio.to_thread(transcribe_audio_groq, temp_file_path)

        if not transcribed_text or not transcribed_text.strip():
            await message.answer(
                "🎙️ <b>لم يتم التعرف على صوت أو كلمات واضحة في الرسالة الصوتية.</b>\n\n"
                "يرجى التحدث بوضوح باللغة الإنجليزية والمحاولة مرة أخرى. ✨",
                reply_markup=get_ai_chat_keyboard(),
                parse_mode="HTML"
            )
            return

        # 3. Retrieve conversational history
        data = await state.get_data()
        history = data.get("history", [])

        # 4. Generate AI tutor feedback in background thread
        ai_reply = await asyncio.to_thread(chat_with_ai_tutor, transcribed_text, history)

        # 5. Append to history
        history.append({"role": "user", "text": transcribed_text})
        history.append({"role": "model", "text": ai_reply})
        if len(history) > 20:
            history = history[-20:]
        await state.update_data(history=history)

        # 6. Format dual-section response as required
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

        # 7. Generate & send voice note with correct pronunciation
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
        # Guarantee cleanup of temporary audio file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass

@ai_router.message(AITutorStates.chatting, F.text)
async def handle_ai_chat_message(message: Message, state: FSMContext):
    """Processes student text messages with AI Tutor, then replies with text and voice note."""
    user_text = message.text.strip()
    if not user_text:
        return

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

    # 1. Send text response
    await message.answer(
        ai_reply,
        reply_markup=get_ai_chat_keyboard()
    )

    # 2. Send TTS voice pronunciation
    await send_tts_voice_response(message, ai_reply)

@ai_router.message(Command("ai"))
async def handle_ai_command(message: Message):
    """Quick one-off question helper."""
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
