import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from app.services.ai_service import chat_with_ai_tutor
from app.bot.keyboards.main_menu import get_main_reply_keyboard, get_ai_chat_keyboard

ai_router = Router(name="ai_router")

class AITutorStates(StatesGroup):
    chatting = State()

@ai_router.message(F.text.contains("المساعد اللغوي") | F.text.contains("AI Tutor"))
async def handle_start_ai_tutor_chat(message: Message, state: FSMContext):
    """Activates AI English Tutor conversation mode."""
    await state.set_state(AITutorStates.chatting)
    await state.update_data(history=[])

    welcome_text = (
        "🤖 <b>مرحباً بك في خدمة المساعد اللغوي الذكي (AI English Tutor)!</b> 🎓\n\n"
        "أنا هنا لمساعدتك على ممارسة وتطوير لغتك الإنجليزية، وتصحيح أي أخطاء قواعدية أو إملائية بلطف ودقة.\n\n"
        "💬 <b>كيف تبدأ؟</b>\n"
        "اكتب أي رسالة أو جملة باللغة الإنجليزية في المحادثة أدناه، وسأقوم بالرد عليك ومساعدتك فوراً!\n\n"
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

@ai_router.message(AITutorStates.chatting, F.text)
async def handle_ai_chat_message(message: Message, state: FSMContext):
    """Processes student messages with Gemini 1.5 Flash in conversation mode."""
    user_text = message.text.strip()
    if not user_text:
        return

    # Visual typing indicator
    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except Exception:
        pass

    # Retrieve conversational history
    data = await state.get_data()
    history = data.get("history", [])

    # Run in thread pool to prevent blocking the async event loop
    ai_reply = await asyncio.to_thread(chat_with_ai_tutor, user_text, history)

    # Append to history and keep last 20 messages
    history.append({"role": "user", "text": user_text})
    history.append({"role": "model", "text": ai_reply})
    if len(history) > 20:
        history = history[-20:]
    await state.update_data(history=history)

    await message.answer(
        ai_reply,
        reply_markup=get_ai_chat_keyboard()
    )

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
