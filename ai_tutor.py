from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from app.services.ai_service import get_ai_tutor_response

ai_router = Router(name="ai_router")

@ai_router.message(Command("ai"))
async def handle_ai_command(message: Message):
    """Allows students to ask questions to the AI Tutor."""
    # Extract the question after '/ai '
    question = message.text.replace("/ai", "", 1).strip() if message.text else ""

    if not question:
        help_msg = (
            "🤖 <b>Fluence Academy AI Tutor</b>\n\n"
            "Ask any question about English grammar, vocabulary, pronunciation, or lessons!\n\n"
            "<b>Usage:</b>\n"
            "Type <code>/ai</code> followed by your question.\n\n"
            "<b>Example:</b>\n"
            "<code>/ai What is the difference between 'affect' and 'effect'?</code>"
        )
        await message.answer(help_msg, parse_mode="HTML")
        return

    # Indicate typing action
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # Get response from AI service
    response = get_ai_tutor_response(student_question=question)
    await message.answer(response, parse_mode="HTML")
