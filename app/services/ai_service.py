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

# Credentials & Active AI Model Configurations
DEFAULT_GROQ_API_KEY = "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"
DEFAULT_GEMINI_API_KEY = "AQ.Ab8RN6LFDPHEQNAEPrx6x3PlcZFKYQl0wLs4ZJzsQ9xx0Dwo2Q"

GROQ_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "allam-2-7b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant"
]

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
    Sends message to AI Tutor (supports Groq & Gemini seamlessly).
    Catches all exceptions gracefully to ensure the bot never halts or crashes.
    """
    groq_key = os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    gemini_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)

    if gemini_key and str(gemini_key).strip().strip("'\"").startswith("gsk_"):
        groq_key = str(gemini_key).strip().strip("'\"")

    # 1. Primary Engine: Groq (Qwen 27B / GPT-OSS 120B / 20B)
    if groq_key and str(groq_key).strip().strip("'\"").startswith("gsk_"):
        try:
            return chat_with_groq(str(groq_key).strip().strip("'\""), user_message, history)
        except Exception as e:
            logger.error(f"[Groq AI Tutor Error] {e}")
            print(f"[Groq AI Tutor Exception] {e}")

    # 2. Secondary Engine: Google Gemini (if valid key is provided)
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
            print(f"[Gemini AI Tutor Exception] {e}")

    # Fallback message
    return (
        "⚠️ <b>عذراً، المساعد اللغوي غير متاح حالياً</b>\n\n"
        "حدث خطأ أثناء الاتصال بمزود الذكاء الاصطناعي. "
        "يرجى المحاولة مرة أخرى لاحقاً."
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
    Converts English AI tutor response to high quality speech using gTTS.
    Uses British accent ('co.uk') for academy standard pronunciation.
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
                timeout=45
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

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    messages = [
        {"role": "system", "content": DAILY_CHALLENGE_SYSTEM_INSTRUCTION},
        {"role": "user", "content": "Give me a challenge"}
    ]

    for model_name in GROQ_MODELS:
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={"model": model_name, "messages": messages, "temperature": 0.8, "max_tokens": 400},
                timeout=25
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

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    messages = [
        {"role": "system", "content": DAILY_CHALLENGE_SYSTEM_INSTRUCTION},
        {"role": "user", "content": "Give me a challenge"},
        {"role": "assistant", "content": question},
        {"role": "user", "content": f"My answer is: {user_answer}"}
    ]

    for model_name in GROQ_MODELS:
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={"model": model_name, "messages": messages, "temperature": 0.4, "max_tokens": 600},
                timeout=25
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
        "topic": "Make vs. Do in English Collocations",
        "info": "A very common mistake in English is confusing <b>Make</b> and <b>Do</b>!\n\n• <b>DO</b> is used for daily chores, jobs, and general unspecified activities: <i>do homework, do business, do your best, do research</i>.\n• <b>MAKE</b> is used for creating, producing, or causing something to happen: <i>make a decision, make a mistake, make coffee, make money, make progress</i>.\n\n<b>Example:</b> 'I need to <b>do</b> my homework before I <b>make</b> a phone call.'",
        "audio_text": "Please do your best and do not worry if you make a mistake.",
        "questions": [
            {
                "question": "Which verb correctly completes: 'Please don't _____ any excuses.'",
                "options": [
                    "do",
                    "make",
                    "create",
                    "perform"
                ],
                "correct_index": 1,
                "explanation": "We say 'make an excuse' (not 'do an excuse')."
            },
            {
                "question": "Which phrase is correct in English?",
                "options": [
                    "Make research",
                    "Do a mistake",
                    "Do business",
                    "Make homework"
                ],
                "correct_index": 2,
                "explanation": "We say 'do business' and 'do research', while for mistakes we say 'make a mistake'."
            }
        ]
    },
    {
        "topic": "Phrasal Verbs: Look after vs. Look into",
        "info": "Phrasal verbs change meaning completely based on the preposition!\n\n• <b>Look after</b>: To take care of someone or something.\n<i>Example: 'Can you look after my cat while I am on vacation?'</i>\n\n• <b>Look into</b>: To investigate, examine, or research a problem.\n<i>Example: 'The committee will look into the complaints tomorrow.'</i>",
        "audio_text": "The manager promised to look into the issue while I look after the office.",
        "questions": [
            {
                "question": "Complete: 'The detective promised to _____ the mysterious case.'",
                "options": [
                    "look after",
                    "look into",
                    "look up",
                    "look for"
                ],
                "correct_index": 1,
                "explanation": "'Look into' means to investigate or examine thoroughly."
            },
            {
                "question": "What does 'She looks after her elderly parents' mean?",
                "options": [
                    "She investigates them",
                    "She takes care of them",
                    "She looks like them",
                    "She visits them rarely"
                ],
                "correct_index": 1,
                "explanation": "'Look after' means to provide care and support."
            }
        ]
    }
]

def generate_daily_lesson_and_quiz(api_key: Optional[str] = None) -> dict:
    """
    Generates a dynamic daily English lesson with clear explanations and 2 questions testing that info.
    Returns a dict with: topic, info, audio_text, and questions.
    """
    import json
    key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or DEFAULT_GROQ_API_KEY
    if key:
        key = str(key).strip().strip("'\"")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    prompt = (
        "Generate a fresh, engaging daily English learning bite/lesson followed by 2 multiple-choice questions "
        "strictly testing that specific information.\n"
        "Output strictly valid JSON with this exact structure:\n"
        "{\n"
        '  "topic": "Topic Title",\n'
        '  "info": "Clear pedagogical explanation in English with examples (and brief Arabic explanation where helpful).",\n'
        '  "audio_text": "A clear, natural 1-2 sentence example suitable for TTS British audio listening.",\n'
        '  "questions": [\n'
        "    {\n"
        '      "question": "Question text testing the above rule?",\n'
        '      "options": ["Option A", "Option B", "Option C", "Option D"],\n'
        '      "correct_index": 0,\n'
        '      "explanation": "Brief explanation of why this answer is correct."\n'
        "    },\n"
        "    {\n"
        '      "question": "Second question testing the rule?",\n'
        '      "options": ["Option A", "Option B", "Option C", "Option D"],\n'
        '      "correct_index": 1,\n'
        '      "explanation": "Brief explanation of why this answer is correct."\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    payload = {
        "model": GROQ_MODELS[0],
        "messages": [
            {"role": "system", "content": "You are a master English educator at Fluence Academy. Output valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }

    for model_name in GROQ_MODELS:
        payload["model"] = model_name
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=25)
            if resp.status_code == 200:
                raw_content = resp.json()["choices"][0]["message"]["content"]
                data = json.loads(raw_content)
                if "topic" in data and "questions" in data and len(data["questions"]) >= 2:
                    return data
        except Exception as e:
            logger.warning(f"[Daily Lesson Gen Warning with {model_name}] {e}")
            continue

    # Fallback to rotating curated curriculum
    day_idx = datetime.now().day % len(CURATED_DAILY_LESSONS)
    return CURATED_DAILY_LESSONS[day_idx]

# =========================================================================
# Daily English Lesson & Scheduler Engine (Fail-safe Unified Service)
# =========================================================================

_CURRENT_DAILY_LESSON = None
_LAST_GENERATED_DATE = None

def get_today_lesson(force_refresh: bool = False) -> dict:
    """Returns today's cached lesson or generates a fresh one."""
    global _CURRENT_DAILY_LESSON, _LAST_GENERATED_DATE
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if force_refresh or _CURRENT_DAILY_LESSON is None or _LAST_GENERATED_DATE != today_str:
        try:
            _CURRENT_DAILY_LESSON = generate_daily_lesson_and_quiz()
            _LAST_GENERATED_DATE = today_str
            print(f"[Scheduler LOG] Generated fresh daily lesson: {_CURRENT_DAILY_LESSON.get('topic')}", flush=True)
        except Exception as e:
            logger.error(f"[Scheduler Error] Generating lesson failed: {e}")
            if _CURRENT_DAILY_LESSON is None:
                _CURRENT_DAILY_LESSON = CURATED_DAILY_LESSONS[0]
                _LAST_GENERATED_DATE = today_str

    return _CURRENT_DAILY_LESSON

def build_daily_lesson_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for the daily lesson message."""
    keyboard = [
        [InlineKeyboardButton(text="🚀 ابدأ اختبار هذه المعلومة الآن (Quiz)", callback_data="start_daily_info_quiz")],
        [
            InlineKeyboardButton(text="🔄 معلومة واختبار آخر", callback_data="refresh_daily_lesson"),
            InlineKeyboardButton(text="🔙 قسم الاختبارات", callback_data="back_to_quizzes_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def send_daily_lesson_to_user(bot: Bot, chat_id: int, lesson_data: dict, send_voice: bool = True) -> bool:
    """Sends the formatted daily educational info, optional voice pronunciation, and quiz button."""
    try:
        topic = lesson_data.get("topic", "Daily English Tip")
        info = lesson_data.get("info", "")
        audio_text = lesson_data.get("audio_text") or info

        caption = (
            f"💡 <b>معلومة اليوم الأكاديمية (Daily English Bite)</b> 🎓\n"
            f"📌 <b>الموضوع:</b> {topic}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{info}\n\n"
            f"🎧 <i>استمع إلى التسجيل الصوتي أدناه للتدرب على النطق واللفظ الصحيح (British English).</i>\n"
            f"👇 <i>ثم اضغط على الزر أدناه لبدء اختبار الفهم لهذه المعلومة!</i>"
        )

        await bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=build_daily_lesson_keyboard(),
            parse_mode="HTML"
        )

        if send_voice and audio_text:
            storage_dir = "storage"
            os.makedirs(storage_dir, exist_ok=True)
            temp_audio = os.path.join(storage_dir, f"daily_voice_{chat_id}_{int(datetime.now().timestamp())}.mp3")
            try:
                await asyncio.to_thread(text_to_speech_gtts, audio_text, temp_audio, "en", "co.uk")
                if os.path.exists(temp_audio) and os.path.getsize(temp_audio) > 0:
                    voice_file = FSInputFile(temp_audio)
                    await bot.send_voice(
                        chat_id=chat_id,
                        voice=voice_file,
                        caption=f"🗣️ <i>نطق الجملة النموذجية الخاصة بمعلومة:</i> <b>{topic}</b>",
                        parse_mode="HTML"
                    )
            except Exception as v_err:
                logger.warning(f"[Voice Send Warning for {chat_id}] {v_err}")
            finally:
                if os.path.exists(temp_audio):
                    try:
                        os.remove(temp_audio)
                    except Exception:
                        pass

        return True
    except Exception as e:
        logger.warning(f"[Daily Lesson Send Error to {chat_id}] {e}")
        return False

async def broadcast_daily_lesson(bot: Bot) -> int:
    """Broadcasts today's lesson to all registered active students in the database."""
    lesson = get_today_lesson(force_refresh=True)
    sent_count = 0

    print(f"[Scheduler LOG] Starting daily broadcast: '{lesson.get('topic')}'...", flush=True)

    async with AsyncSessionLocal() as session:
        q = select(User).where(User.telegram_id.isnot(None), User.is_active == True)
        res = await session.execute(q)
        users = res.scalars().all()

    for u in users:
        try:
            success = await send_daily_lesson_to_user(bot, u.telegram_id, lesson, send_voice=True)
            if success:
                sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as err:
            logger.warning(f"[Broadcast Error for user {u.telegram_id}] {err}")

    print(f"[Scheduler LOG] Broadcast completed: Sent to {sent_count}/{len(users)} students.", flush=True)
    return sent_count

async def start_daily_scheduler(bot: Bot):
    """
    Background scheduler loop that triggers daily English lesson and quiz broadcast.
    Runs continuously alongside the Telegram Bot.
    """
    print("⏰ [Daily Scheduler] Background service started successfully.", flush=True)
    await asyncio.sleep(10)

    try:
        get_today_lesson()
    except Exception:
        pass

    while True:
        try:
            now = datetime.now(timezone.utc)
            target_hour = 8
            if now.hour >= target_hour:
                next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
                next_run_timestamp = next_run.timestamp() + 86400
            else:
                next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
                next_run_timestamp = next_run.timestamp()

            wait_seconds = max(60, int(next_run_timestamp - now.timestamp()))
            print(f"⏰ [Daily Scheduler] Next scheduled broadcast in {wait_seconds // 3600}h {(wait_seconds % 3600) // 60}m.", flush=True)

            while wait_seconds > 0:
                sleep_chunk = min(1800, wait_seconds)
                await asyncio.sleep(sleep_chunk)
                wait_seconds -= sleep_chunk

            await broadcast_daily_lesson(bot)

        except asyncio.CancelledError:
            print("🛑 [Daily Scheduler] Cancelled.", flush=True)
            break
        except Exception as e:
            logger.error(f"[Daily Scheduler Error] {e}", exc_info=True)
            await asyncio.sleep(300)

# =========================================================================
# Official PDF Certificate Generator Engine Re-export
# =========================================================================
try:
    from app.services.certificate_service import create_certificate_pdf, sanitize_pdf_text
except Exception:
    pass
