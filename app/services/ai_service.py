import os
import logging
import warnings
import requests
import re
from typing import Optional, List, Dict
from app.core.config import settings

warnings.filterwarnings("ignore", category=FutureWarning)

logger = logging.getLogger(__name__)

# Credentials & Model Config
DEFAULT_GROQ_API_KEY = "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"
DEFAULT_GEMINI_API_KEY = "AQ.Ab8RN6LFDPHEQNAEPrx6x3PlcZFKYQl0wLs4ZJzsQ9xx0Dwo2Q"

GROQ_MODELS = ["openai/gpt-oss-120b", "llama3-70b-8192", "llama-3.3-70b-versatile", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]

SYSTEM_INSTRUCTION = (
    "You are a friendly and professional English language tutor at Fluence English Academy. "
    "Your job is to chat with students in English, gently correct their grammar, spelling, "
    "or vocabulary mistakes, and encourage them to keep practicing. Always be supportive and use a professional yet warm tone."
)

ACADEMIC_WRITING_SYSTEM_INSTRUCTION = (
    "You are an expert University Professor of English Language and Literature at Fluence English Academy. "
    "Your task is to evaluate and proofread academic writing, essays, and literature analyses submitted by university students.\n\n"
    "Strictly focus on:\n"
    "1. Academic tone and formal vocabulary.\n"
    "2. Correct usage of transition signals and coherence.\n"
    "3. Grammatical accuracy and sentence variety.\n"
    "4. If the text discusses literature, assume the context is World Literature (especially Poetry and Drama).\n\n"
    "Provide your feedback in this format:\n\n"
    "📊 Overall Score (Out of 10)\n\n"
    "🧐 Critique & Errors (Point out specific mistakes)\n\n"
    "✨ Polished Academic Version (Rewrite the text professionally)."
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

def review_academic_writing(student_text: str, api_key: Optional[str] = None) -> str:
    """
    Evaluates and proofreads university-level academic writing and essays using Groq.
    """
    key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    if key:
        key = str(key).strip().strip("'\"")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    messages = [
        {"role": "system", "content": ACADEMIC_WRITING_SYSTEM_INSTRUCTION},
        {"role": "user", "content": student_text}
    ]

    for model_name in GROQ_MODELS:
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={
                    "model": model_name,
                    "messages": messages,
                    "temperature": 0.4,
                    "max_tokens": 1500
                },
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                logger.warning(f"[Academic Review {model_name} Warning] {resp.status_code}: {resp.text}")
        except Exception as err:
            logger.warning(f"[Academic Review Exception with {model_name}] {err}")
            continue

    raise Exception("All models failed to review academic writing.")

def transcribe_audio_groq(file_path: str, api_key: Optional[str] = None) -> str:
    """
    Transcribes student English voice notes using Groq Whisper models (whisper-large-v3).
    """
    key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    if key:
        key = str(key).strip().strip("'\"")

    try:
        from groq import Groq
        client = Groq(api_key=key)
        with open(file_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(file_path), f.read()),
                model="whisper-large-v3",
                language="en",
                response_format="json"
            )
            if transcription and transcription.text:
                return transcription.text.strip()
    except Exception as sdk_err:
        logger.warning(f"[Groq SDK Whisper Warning] {sdk_err}, trying direct HTTP...")

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {key}"}
    for model_name in ["whisper-large-v3", "whisper-large-v3-turbo"]:
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "audio/ogg")}
                data = {
                    "model": model_name,
                    "language": "en",
                    "response_format": "json"
                }
                resp = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                if resp.status_code == 200:
                    text = resp.json().get("text", "").strip()
                    if text:
                        return text
                else:
                    logger.warning(f"[Groq HTTP {model_name} Error] {resp.status_code}: {resp.text}")
        except Exception as http_err:
            logger.warning(f"[Groq HTTP Exception {model_name}] {http_err}")

    raise Exception("Could not transcribe audio using Groq Whisper.")

def clean_text_for_tts(text: str) -> str:
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"[*_`#~]", "", clean)
    clean = re.sub(r"[^\w\s.,!?'\"-]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def text_to_speech_gtts(text: str, output_path: str, lang: str = "en", tld: str = "co.uk") -> str:
    from gtts import gTTS
    cleaned_text = clean_text_for_tts(text)
    if not cleaned_text:
        cleaned_text = "Keep practicing English every day!"
    
    tts = gTTS(text=cleaned_text, lang=lang, tld=tld, slow=False)
    tts.save(output_path)
    return output_path

def get_configured_model():
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
