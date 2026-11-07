import os
import logging
from typing import Optional, List, Dict
import requests
from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_GROQ_API_KEY = "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"

SYSTEM_INSTRUCTION = (
    "You are the Lead English Professor and AI Tutor at Fluence English Academy. "
    "Fluence Academy is a premier English learning institution providing university-level and communicative English.\n\n"
    "Your teaching style is:\n"
    "1. Always encouraging, friendly, and pedagogically sound.\n"
    "2. When answering English queries, provide clear explanations with natural practical examples.\n"
    "3. If the student makes a grammar, vocabulary, or spelling mistake in English, gently point it out and provide the natural correction.\n"
    "4. Support both Arabic and English questions. If asked in Arabic, explain in clear Arabic while keeping terminology and examples in English.\n"
    "5. Keep answers well-formatted, concise, and structured for Telegram readability."
)

def chat_with_groq(api_key: str, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """Calls Groq Cloud API with OpenAI-compatible endpoint."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    if history:
        for item in history[-10:]:
            role = "user" if item.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": item.get("text", "")})

    messages.append({"role": "user", "content": user_message})

    preferred_models = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile",
        "llama3-8b-8192",
        "qwen/qwen3.8-27b"
    ]

    for model_name in preferred_models:
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                logger.warning(f"[Groq Model {model_name} HTTP {resp.status_code}] {resp.text}")
        except Exception as err:
            logger.warning(f"[Groq Exception with {model_name}] {err}")
            continue

    raise Exception("All Groq chat models failed to produce a response.")

def transcribe_audio_groq(file_path: str, api_key: Optional[str] = None) -> str:
    """Transcribes an audio file into English text using Groq's Whisper API."""
    key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    if key:
        key = str(key).strip().strip("'\"")

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {key}"}

    for model in ["whisper-large-v3", "whisper-large-v3-turbo"]:
        try:
            with open(file_path, "rb") as audio_file:
                files = {"file": (os.path.basename(file_path), audio_file, "audio/ogg")}
                data = {
                    "model": model,
                    "response_format": "json",
                    "language": "en"
                }
                resp = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                if resp.status_code == 200:
                    result = resp.json()
                    return result.get("text", "").strip()
                else:
                    logger.warning(f"[Whisper Model {model} HTTP {resp.status_code}]: {resp.text}")
        except Exception as e:
            logger.warning(f"[Whisper Exception with {model}]: {e}")
            continue

    raise Exception("Groq Whisper transcription failed for all models.")

def get_configured_model():
    """Fallback Google Gemini configuration."""
    import google.generativeai as genai
    gemini_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY is not set.")
    genai.configure(api_key=gemini_key)
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_INSTRUCTION
    )

def chat_with_ai_tutor(user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """Primary chat handler with Groq."""
    groq_key = os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    gemini_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)

    if groq_key and str(groq_key).strip().strip("'\"").startswith("gsk_"):
        try:
            return chat_with_groq(str(groq_key).strip().strip("'\""), user_message, history)
        except Exception as e:
            logger.error(f"[Groq AI Tutor Error] {e}")

    if gemini_key and not str(gemini_key).strip().strip("'\"").startswith("gsk_"):
        try:
            model = get_configured_model()
            formatted_history = []
            if history:
                for item in history:
                    role = "user" if item.get("role") == "user" else "model"
                    formatted_history.append({"role": role, "parts": [item.get("text", "")]})
            chat = model.start_chat(history=formatted_history)
            response = chat.send_message(user_message)
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            logger.error(f"[Gemini AI Tutor Error] {e}")

    return (
        "⚠️ <b>عذراً، المساعد اللغوي غير متاح حالياً</b>\n\n"
        "حدث خطأ أثناء الاتصال بمزود الذكاء الاصطناعي. يرجى المحاولة لاحقاً."
    )

def clean_text_for_tts(text: str) -> str:
    """Cleans markdown, html tags, and excessive formatting for smooth TTS reading."""
    import re
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"[*_`#~]", "", clean)
    clean = re.sub(r"[^\w\s.,!?'\"-]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def text_to_speech_gtts(text: str, output_path: str, lang: str = "en", tld: str = "co.uk") -> str:
    """Converts English response to speech using gTTS (British Accent)."""
    from gtts import gTTS
    cleaned_text = clean_text_for_tts(text)
    if not cleaned_text:
        cleaned_text = "Good job! Keep practicing English every day."
    tts = gTTS(text=cleaned_text, lang=lang, tld=tld, slow=False)
    tts.save(output_path)
    return output_path

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

def review_academic_writing(student_text: str, api_key: Optional[str] = None) -> str:
    """Evaluates and proofreads university academic writing using Groq."""
    key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    if key:
        key = str(key).strip().strip("'\"")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    messages = [
        {"role": "system", "content": ACADEMIC_WRITING_SYSTEM_INSTRUCTION},
        {"role": "user", "content": student_text}
    ]

    for model_name in ["openai/gpt-oss-120b", "llama3-70b-8192", "llama-3.3-70b-versatile", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]:
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={"model": model_name, "messages": messages, "temperature": 0.4, "max_tokens": 1500},
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            else:
                logger.warning(f"[Academic Review {model_name} Warning] {resp.status_code}: {resp.text}")
        except Exception as err:
            logger.warning(f"[Academic Review Exception with {model_name}] {err}")
            continue

    raise Exception("All models failed to review academic writing.")

DAILY_CHALLENGE_SYSTEM_INSTRUCTION = (
    "You are the Daily Challenge Quizmaster at Fluence English Academy.\n"
    "When the user asks for a challenge, generate exactly ONE engaging multiple-choice or fill-in-the-blank question about English grammar, phrasal verbs, or collocations.\n"
    "DO NOT provide the answer yet. Wait for the user to reply.\n"
    "When the user replies with their answer, evaluate it: tell them if it's correct or incorrect, provide the right answer with a brief, clear explanation, and encourage them."
)

def generate_daily_challenge(api_key: Optional[str] = None) -> str:
    """Generates a single multiple-choice or fill-in-the-blank challenge."""
    key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    if key:
        key = str(key).strip().strip("'\"")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    messages = [
        {"role": "system", "content": DAILY_CHALLENGE_SYSTEM_INSTRUCTION},
        {"role": "user", "content": "Give me a challenge"}
    ]

    for model_name in ["openai/gpt-oss-20b", "llama3-8b-8192", "openai/gpt-oss-120b", "llama-3.3-70b-versatile", "qwen/qwen3.8-27b"]:
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={"model": model_name, "messages": messages, "temperature": 0.8, "max_tokens": 400},
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            continue

    raise Exception("Failed to generate daily challenge.")

def evaluate_daily_challenge(question: str, user_answer: str, api_key: Optional[str] = None) -> str:
    """Evaluates the student's answer to the challenge question."""
    key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    if key:
        key = str(key).strip().strip("'\"")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    messages = [
        {"role": "system", "content": DAILY_CHALLENGE_SYSTEM_INSTRUCTION},
        {"role": "user", "content": "Give me a challenge"},
        {"role": "assistant", "content": question},
        {"role": "user", "content": f"My answer is: {user_answer}"}
    ]

    for model_name in ["openai/gpt-oss-20b", "llama3-8b-8192", "openai/gpt-oss-120b", "llama-3.3-70b-versatile", "qwen/qwen3.8-27b"]:
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={"model": model_name, "messages": messages, "temperature": 0.5, "max_tokens": 500},
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            continue

    raise Exception("Failed to evaluate daily challenge answer.")
