from typing import Optional
from google import genai
from app.core.config import settings

def get_ai_tutor_response(student_question: str, context: Optional[str] = None) -> str:
    """
    Asks Google Gemini to act as a helpful, encouraging Fluence Academy English tutor.
    Returns AI answer or fallback message if disabled.
    """
    if not settings.AI_ENABLED or not settings.GEMINI_API_KEY:
        return (
            "🤖 <b>AI Tutor Notice</b>\n\n"
            "The AI Smart Tutor is currently offline or undergoing scheduled maintenance.\n"
            "Please check back soon, or ask your question in our official channel: <b>@FluenceEnglish</b>!"
        )

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        system_instruction = (
            "You are Fluence Academy's AI English Tutor. You are friendly, encouraging, and clear. "
            "Explain concepts simply for English language learners. Keep explanations concise, polite, "
            "and provide illustrative examples with correct grammar and pronunciation tips."
        )

        prompt = f"Student Question: {student_question}"
        if context:
            prompt = f"Context (Lesson Material):\n{context}\n\n{prompt}"

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=dict(system_instruction=system_instruction)
        )
        return response.text or "I could not generate an answer right now. Please try again."
    except Exception as e:
        print(f"[AI Service Error] {e}")
        return "⚠️ Our AI Tutor is currently experiencing high demand. Please try asking again in a moment."
