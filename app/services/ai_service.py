import os
import json
import asyncio
import logging
import warnings
import requests
from typing import Optional, List, Dict
from datetime import datetime, timezone
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from sqlalchemy import select

from app.core.config import settings
from app.database.connection import AsyncSessionLocal
from app.database.models import User

# Suppress deprecation notice from google-generativeai
warnings.filterwarnings("ignore", category=FutureWarning)

logger = logging.getLogger(__name__)

# Credentials & Model Config
DEFAULT_GROQ_API_KEY = "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"
DEFAULT_GEMINI_API_KEY = "AQ.Ab8RN6LFDPHEQNAEPrx6x3PlcZFKYQl0wLs4ZJzsQ9xx0Dwo2Q"

GROQ_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "allam-2-7b"
]

SYSTEM_INSTRUCTION = (
    "You are a friendly and professional English language tutor at Fluence English Academy. "
    "Your job is to chat with students in English, gently correct their grammar, spelling, "
    "or vocabulary mistakes, and encourage them to keep practicing. Always be supportive and use a professional yet warm tone."
)

def chat_with_groq(api_key: str, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """High-speed AI Tutor provider: Groq Cloud (Qwen 3.8 27B / GPT-OSS 120B)."""
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION}
    ]
    if history:
        for item in history:
            role = "user" if item.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": item.get("text", "")})
    messages.append({"role": "user", "content": user_message})

    # Method 1: Official Groq Python SDK (direct TLS, HTTP/2, cloudflare-friendly)
    try:
        from groq import Groq
        client = Groq(api_key=api_key, timeout=15.0)
        for model_name in GROQ_MODELS:
            try:
                completion = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1024
                )
                if completion and completion.choices and completion.choices[0].message.content:
                    return completion.choices[0].message.content.strip()
            except Exception as model_err:
                logger.warning(f"[Groq SDK {model_name} Warning] {model_err}")
                continue
    except Exception as sdk_init_err:
        logger.warning(f"[Groq SDK Init Warning] {sdk_init_err}, trying direct HTTP...")

    # Method 2: Direct HTTP fallback
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "FluenceAcademy/2.0 (Official Educational Bot)"
    }
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
                logger.warning(f"[Groq HTTP Warning] {last_error}")
        except Exception as err:
            last_error = str(err)
            continue

    raise Exception(f"All Groq models failed. Last error: {last_error}")

def transcribe_audio_groq(file_path: str, api_key: Optional[str] = None) -> str:
    """
    Transcribes student English voice notes using Groq Whisper models (whisper-large-v3).
    Supports both official groq SDK and direct HTTP fallback.
    """
    key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    if key:
        key = str(key).strip().strip("'\"")

    # Method 1: Try official groq SDK
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

    # Method 2: Direct HTTP fallback
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {key}", "User-Agent": "FluenceAcademy/2.0"}
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
    """
    Sends message to AI Tutor (supports Groq Qwen/GPT-OSS & Gemini seamlessly).
    Catches all exceptions gracefully to ensure the bot never halts or crashes.
    """
    groq_key = os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    gemini_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)

    if gemini_key and str(gemini_key).strip().strip("'\"").startswith("gsk_"):
        groq_key = str(gemini_key).strip().strip("'\"")

    # 1. Primary Engine: Groq (Qwen 27B / GPT-OSS 120B)
    if groq_key and str(groq_key).strip().strip("'\"").startswith("gsk_"):
        try:
            return chat_with_groq(str(groq_key).strip().strip("'\""), user_message, history)
        except Exception as e:
            logger.error(f"[Groq AI Tutor Error] {e}")
            print(f"[Groq AI Tutor Exception] {e}", flush=True)

    # 2. Secondary Engine: Google Gemini
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
            print(f"[Gemini AI Tutor Exception] {e}", flush=True)

    return (
        "Hello! I am your AI Tutor at Fluence English Academy. 🌟\n\n"
        "I noticed your message: <i>\"" + user_message[:60] + "...\"</i>.\n"
        "Keep up the great work practicing English! Try asking me a question about grammar, idioms, or conversation."
    )

def get_ai_tutor_response(student_question: str, context: Optional[str] = None) -> str:
    """Legacy helper for single-turn queries."""
    full_prompt = student_question
    if context:
        full_prompt = f"Context:\n{context}\n\nQuestion: {student_question}"
    return chat_with_ai_tutor(full_prompt)

def clean_text_for_tts(text: str) -> str:
    """Cleans markdown, html tags, and excessive formatting for smooth TTS reading."""
    import re
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"[*_`#~]", "", clean)
    clean = re.sub(r"[^\w\s.,!?'\"-]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def text_to_speech_gtts(text: str, output_path: str, lang: str = "en", tld: str = "co.uk") -> str:
    """
    Converts English AI tutor response to speech using gTTS (British Accent).
    """
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
    """
    Evaluates and proofreads university-level academic writing and essays using Groq.
    """
    key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    if key:
        key = str(key).strip().strip("'\"")

    messages = [
        {"role": "system", "content": ACADEMIC_WRITING_SYSTEM_INSTRUCTION},
        {"role": "user", "content": student_text}
    ]

    # Method 1: Official Groq SDK
    try:
        from groq import Groq
        client = Groq(api_key=key, timeout=30.0)
        for model_name in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "allam-2-7b"]:
            try:
                comp = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.4,
                    max_tokens=1500
                )
                if comp and comp.choices and comp.choices[0].message.content:
                    return comp.choices[0].message.content.strip()
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"[Academic Review SDK Error] {e}")

    # Method 2: HTTP fallback
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "FluenceAcademy/2.0 (Official Educational Bot)"
    }
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
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            continue

    raise Exception("All models failed to review academic writing.")

DAILY_CHALLENGE_SYSTEM_INSTRUCTION = (
    "You are the Daily Challenge Quizmaster at Fluence English Academy.\n"
    "When the user asks for a challenge, generate exactly ONE engaging multiple-choice or fill-in-the-blank question about English grammar, phrasal verbs, or collocations.\n"
    "DO NOT provide the answer yet. Wait for the user to reply.\n"
    "When the user replies with their answer, evaluate it: tell them if it's correct or incorrect, provide the right answer with a brief, clear explanation, and encourage them."
)

def generate_daily_challenge(api_key: Optional[str] = None) -> str:
    """Generates a fresh single multiple-choice or fill-in-the-blank challenge."""
    key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    if key:
        key = str(key).strip().strip("'\"")

    messages = [
        {"role": "system", "content": DAILY_CHALLENGE_SYSTEM_INSTRUCTION},
        {"role": "user", "content": "Give me a fresh English grammar or vocabulary challenge question with 4 multiple choice options (A, B, C, D). Do not provide the answer."}
    ]

    # Method 1: Groq SDK
    try:
        from groq import Groq
        client = Groq(api_key=key, timeout=20.0)
        for model_name in ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "allam-2-7b"]:
            try:
                comp = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.8,
                    max_tokens=400
                )
                if comp and comp.choices and comp.choices[0].message.content:
                    return comp.choices[0].message.content.strip()
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"[Daily Challenge SDK Error] {e}")

    # Method 2: HTTP
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "FluenceAcademy/2.0"}
    for model_name in GROQ_MODELS:
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={"model": model_name, "messages": messages, "temperature": 0.8, "max_tokens": 400},
                timeout=20
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            continue
    raise Exception("Failed to generate daily challenge from Groq.")

def evaluate_daily_challenge(question: str, user_answer: str, api_key: Optional[str] = None) -> str:
    """Evaluates student's answer against the generated challenge question."""
    key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    if key:
        key = str(key).strip().strip("'\"")

    messages = [
        {"role": "system", "content": DAILY_CHALLENGE_SYSTEM_INSTRUCTION},
        {"role": "user", "content": "Give me a challenge"},
        {"role": "assistant", "content": question},
        {"role": "user", "content": f"My answer is: {user_answer}"}
    ]

    # Method 1: Groq SDK
    try:
        from groq import Groq
        client = Groq(api_key=key, timeout=20.0)
        for model_name in ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "allam-2-7b"]:
            try:
                comp = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.4,
                    max_tokens=600
                )
                if comp and comp.choices and comp.choices[0].message.content:
                    return comp.choices[0].message.content.strip()
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"[Evaluate Challenge SDK Error] {e}")

    # Method 2: HTTP
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "FluenceAcademy/2.0"}
    for model_name in GROQ_MODELS:
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={"model": model_name, "messages": messages, "temperature": 0.4, "max_tokens": 600},
                timeout=20
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            continue
    raise Exception("Failed to evaluate daily challenge from Groq.")

CURATED_DAILY_LESSONS = [
    {
        "topic": "Since vs. For with Present Perfect",
        "info": "We use the Present Perfect to describe actions that started in the past and continue into the present.\n\n• Use <b>since</b> for a specific starting point in time: <i>since 2015, since Monday, since 9:00 AM</i>.\n• Use <b>for</b> for a duration or period of time: <i>for three years, for two weeks, for an hour</i>.\n\n<b>Examples:</b>\n- 'I have lived here <b>since</b> 2020.'\n- 'I have lived here <b>for</b> four years.'",
        "audio_text": "I have lived here since 2020, and I have worked at this academy for four years.",
        "questions": [
            {
                "question": "Which sentence uses the preposition correctly?",
                "options": [
                    "She has been studying English for 2018.",
                    "She has been studying English since 2018.",
                    "She has been studying English since 5 years.",
                    "She has been studying English for last week."
                ],
                "correct_index": 1,
                "explanation": "'Since' is used with specific starting dates and years, so 'since 2018' is correct."
            },
            {
                "question": "Complete: 'They have been waiting at the airport _____ two hours.'",
                "options": [
                    "since",
                    "for",
                    "from",
                    "during"
                ],
                "correct_index": 1,
                "explanation": "'Two hours' is a duration of time, so 'for' is the correct preposition."
            }
        ]
    },
    {
        "topic": "Academic Transition Signals: However vs. In Addition",
        "info": "In formal academic writing, connecting words (cohesion devices) give your essay flow and logical progression:\n\n• Use <b>However</b> (or <i>Nevertheless</i>) to introduce a contrast or opposing view.\n• Use <b>In addition</b> (or <i>Furthermore</i>, <i>Moreover</i>) to add supporting information to your point.\n\n<b>Tip:</b> Always place a comma after these transitions when starting a new clause or sentence.",
        "audio_text": "Academic writing requires clear transitions. However, many students forget commas.",
        "questions": [
            {
                "question": "Choose the best transition: 'Online education provides flexibility. ______, it requires strong self-discipline.'",
                "options": [
                    "Furthermore",
                    "However",
                    "Because",
                    "Therefore"
                ],
                "correct_index": 1,
                "explanation": "The second sentence introduces an opposing challenge/contrast, so 'However' is the correct signal."
            }
        ]
    },
    {
        "topic": "Essential Phrasal Verb: 'Look Forward To'",
        "info": "The phrase <b>look forward to</b> means to feel excited or pleased about something that is going to happen in the future.\n\n⚠️ <b>Crucial Grammar Rule:</b>\nBecause 'to' here is a preposition (not an infinitive marker), it MUST be followed by a <b>Gerund (verb + -ing)</b> or a noun!\n\n<b>Correct:</b> 'I look forward to <u>meeting</u> you.'\n<b>Incorrect:</b> 'I look forward to <u>meet</u> you.'",
        "audio_text": "I really look forward to hearing your English speaking recordings today.",
        "questions": [
            {
                "question": "Complete the email sign-off correctly: 'We look forward to _____ from you soon.'",
                "options": [
                    "hear",
                    "hearing",
                    "heard",
                    "have heard"
                ],
                "correct_index": 1,
                "explanation": "'Look forward to' is strictly followed by a gerund (-ing), so 'hearing' is correct."
            }
        ]
    }
]

def get_today_curated_lesson() -> Dict:
    """Returns today's curated academic lesson based on day of year."""
    day_index = datetime.now(timezone.utc).timetuple().tm_yday
    return CURATED_DAILY_LESSONS[day_index % len(CURATED_DAILY_LESSONS)]

async def send_daily_lesson_broadcast(bot: Bot):
    """Broadcasts daily lesson and audio pronunciation to all active students."""
    lesson = get_today_curated_lesson()
    text = (
        f"💡 <b>معلومة اليوم الأكاديمية | Daily Lesson</b>\n"
        f"📌 <b>الموضوع:</b> <i>{lesson['topic']}</i>\n"
        f"═" * 32 + "\n\n"
        f"{lesson['info']}\n\n"
        f"🎧 <i>استمع للبصمة الصوتية باللكنة البريطانية المعتمدة أدناه للتمرن على اللفظ!</i>"
    )

    storage_dir = "storage"
    os.makedirs(storage_dir, exist_ok=True)
    audio_path = os.path.join(storage_dir, "daily_lesson.mp3")

    try:
        await asyncio.to_thread(text_to_speech_gtts, lesson["audio_text"], audio_path)
    except Exception as e:
        logger.error(f"[Daily Lesson TTS Error] {e}")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 اختبر فهمك للمعلومة الآن", callback_data="test_daily_lesson")],
        [InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="back_to_main_menu")]
    ])

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.is_active == True))
        users = result.scalars().all()

        for user in users:
            try:
                await bot.send_message(chat_id=user.telegram_id, text=text, parse_mode="HTML")
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    await bot.send_voice(
                        chat_id=user.telegram_id,
                        voice=FSInputFile(audio_path),
                        caption="🎧 <i>استمع إلى اللفظ باللكنة البريطانية (British Accent)</i>",
                        reply_markup=kb,
                        parse_mode="HTML"
                    )
                else:
                    await bot.send_message(chat_id=user.telegram_id, text="👇 اختبر استيعابك:", reply_markup=kb)
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.warning(f"Could not send daily broadcast to {user.telegram_id}: {e}")

async def start_daily_scheduler(bot: Bot):
    """Background scheduler that checks and sends daily lessons every 24 hours."""
    while True:
        try:
            now = datetime.now(timezone.utc)
            # Sends at 09:00 UTC daily
            if now.hour == 9 and now.minute == 0:
                await send_daily_lesson_broadcast(bot)
                await asyncio.sleep(65)
        except Exception as e:
            logger.error(f"[Scheduler Error] {e}")
        await asyncio.sleep(30)
