import os
import logging
import warnings
import requests
from typing import Optional, List, Dict
from app.core.config import settings

warnings.filterwarnings("ignore", category=FutureWarning)

logger = logging.getLogger(__name__)

# Credentials & Model Config
DEFAULT_GROQ_API_KEY = "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"
DEFAULT_GEMINI_API_KEY = "AQ.Ab8RN6LFDPHEQNAEPrx6x3PlcZFKYQl0wLs4ZJzsQ9xx0Dwo2Q"

GROQ_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]

SYSTEM_INSTRUCTION = (
    "You are a friendly and professional English language tutor at Fluence English Academy. "
    "Your job is to chat with students in English, gently correct their grammar, spelling, "
    "or vocabulary mistakes, and encourage them to keep practicing. Always be supportive and use a professional yet warm tone."
)

def chat_with_groq(api_key: str, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """High-speed AI Tutor provider: Groq Cloud (GPT-OSS 120B / 20B / Qwen 27B)."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION}
    ]
    if history:
        for item in history:
            role = "user" if item.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": item.get("text", "")})
    messages.append({"role": "user", "content": user_message})

    last_error = None
    for model_name in GROQ_MODELS:
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={
                    "model": model_name,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1024
                },
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                last_error = f"Model {model_name} returned {resp.status_code}: {resp.text}"
                logger.warning(f"[Groq Warning] {last_error}")
        except Exception as err:
            last_error = str(err)
            continue

    raise Exception(f"All Groq models failed. Last error: {last_error}")

def get_configured_model():
    """Configures and returns the gemini model with System Instruction."""
    import google.generativeai as genai
    
    api_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None) or DEFAULT_GEMINI_API_KEY
    if api_key:
        api_key = str(api_key).strip().strip("'\"")

    genai.configure(api_key=api_key)
    
    for m in ["gemini-flash-latest", "gemini-2.5-flash", "gemini-1.5-flash"]:
        try:
            return genai.GenerativeModel(
                model_name=m,
                system_instruction=SYSTEM_INSTRUCTION
            )
        except Exception:
            continue
    return genai.GenerativeModel(model_name="gemini-flash-latest", system_instruction=SYSTEM_INSTRUCTION)

def chat_with_ai_tutor(user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """Sends message to AI Tutor (supports Groq & Gemini seamlessly)."""
    groq_key = os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    gemini_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)

    if gemini_key and str(gemini_key).strip().strip("'\"").startswith("gsk_"):
        groq_key = str(gemini_key).strip().strip("'\"")

    # 1. Primary Engine: Groq
    if groq_key and str(groq_key).strip().strip("'\"").startswith("gsk_"):
        try:
            return chat_with_groq(str(groq_key).strip().strip("'\""), user_message, history)
        except Exception as e:
            logger.error(f"[Groq AI Tutor Error] {e}")

    # 2. Secondary Engine: Gemini (if valid)
    if gemini_key and not str(gemini_key).strip().strip("'\"").startswith("gsk_") and not str(gemini_key).strip().strip("'\"").startswith("AQ."):
        try:
            model = get_configured_model()
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
        except Exception as e:
            logger.error(f"[Gemini AI Tutor Error] {e}")

    return (
        "⚠️ <b>عذراً، المساعد اللغوي غير متاح حالياً</b>\n\n"
        "حدث خطأ أثناء الاتصال بمزود الذكاء الاصطناعي. "
        "يرجى المحاولة مرة أخرى لاحقاً."
    )

def get_ai_tutor_response(student_question: str, context: Optional[str] = None) -> str:
    full_prompt = student_question
    if context:
        full_prompt = f"Context:\n{context}\n\nQuestion: {student_question}"
    return chat_with_ai_tutor(full_prompt)
