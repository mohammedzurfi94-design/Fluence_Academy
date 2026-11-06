import os
import logging
import warnings
from typing import Optional, List, Dict
from app.core.config import settings

# Suppress deprecation notice from google-generativeai
warnings.filterwarnings("ignore", category=FutureWarning)

logger = logging.getLogger(__name__)

# Credentials & Model Config
DEFAULT_GEMINI_API_KEY = "AQ.Ab8RN6KIoe-DxfExjqaUHi1MFNd1dSldFytJbEDgEiCitJtqYQ"
MODEL_NAME = "gemini-1.5-flash"

SYSTEM_INSTRUCTION = (
    "You are a friendly and professional English language tutor at Fluence English Academy. "
    "Your job is to chat with students in English, gently correct their grammar, spelling, "
    "or vocabulary mistakes, and encourage them to keep practicing. Always be supportive."
)

def get_configured_model():
    """Configures and returns the gemini-1.5-flash model with System Instruction."""
    import google.generativeai as genai
    
    api_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None) or DEFAULT_GEMINI_API_KEY
    if api_key:
        api_key = str(api_key).strip().strip("'\"")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_INSTRUCTION
    )
    return model

def chat_with_ai_tutor(user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Sends message to Gemini 1.5 Flash AI Tutor and returns the response.
    Catches all exceptions gracefully to ensure the bot never halts or crashes.
    """
    try:
        model = get_configured_model()
        
        # Build conversational history if provided
        formatted_history = []
        if history:
            for item in history:
                role = "user" if item.get("role") == "user" else "model"
                parts = [item.get("text", "")]
                formatted_history.append({"role": role, "parts": parts})
        
        chat = model.start_chat(history=formatted_history)
        response = chat.send_message(user_message)
        
        if response and response.text:
            return response.text.strip()
        return "I am here to help you practice English! Could you please tell me more or ask another question?"
        
    except Exception as e:
        logger.error(f"[AI Tutor Error] {e}")
        print(f"[AI Tutor Exception] {e}")
        return (
            "⚠️ <b>عذراً، المساعد اللغوي غير متاح حالياً</b>\n\n"
            "حدث خطأ أثناء الاتصال بمزود الذكاء الاصطناعي (Gemini). "
            "يرجى المحاولة مرة أخرى لاحقاً أو التأكد من إعدادات الربط."
        )

def get_ai_tutor_response(student_question: str, context: Optional[str] = None) -> str:
    """Legacy helper for single-turn queries."""
    full_prompt = student_question
    if context:
        full_prompt = f"Context:\n{context}\n\nQuestion: {student_question}"
    return chat_with_ai_tutor(full_prompt)
