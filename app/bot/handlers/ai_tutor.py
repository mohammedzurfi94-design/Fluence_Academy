"""
Fluence Academy - AI Educational Tutor & Interactive Academic Reviewer
Powered by Groq LLaMA 3.3 70B Versatile & Google gTTS Audio Engine.
"""

import os
import asyncio
import logging
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.services.ai_service import (
    chat_with_ai_tutor,
    review_academic_writing,
    generate_daily_challenge,
    evaluate_daily_challenge,
    text_to_speech_gtts
)
from app.bot.keyboards.ai_keyboards import (
    build_ai_tutor_menu_keyboard,
    build_ai_session_reply_keyboard,
    build_academic_writing_reply_keyboard,
    build_challenge_reply_keyboard,
    build_ai_voice_replay_keyboard
)

logger = logging.getLogger(__name__)
ai_router = Router(name="ai_tutor_system")

class AITutorStates(StatesGroup):
    chatting = State()

class AcademicWritingStates(StatesGroup):
    reviewing = State()

class DailyChallengeStates(StatesGroup):
    waiting_answer = State()

async def send_tts_voice_response(message: Message, text: str, accent: str = "co.uk"):
    """Generates and delivers a British accent voice note asynchronously without blocking."""
    storage_dir = "storage"
    os.makedirs(storage_dir, exist_ok=True)
    temp_voice = os.path.join(storage_dir, f"ai_voice_{message.from_user.id}_{int(datetime.now().timestamp())}.mp3")

    clean_text = text.replace("*", "").replace("#", "").replace("_", "").replace("`", "")
    sentences = clean_text.split(".")
    spoken_sample = ". ".join(sentences[:3]) if len(sentences) >= 3 else clean_text
    if len(spoken_sample) > 280:
        spoken_sample = spoken_sample[:280] + "..."

    try:
        await asyncio.to_thread(text_to_speech_gtts, spoken_sample, temp_voice, "en", accent)
        if os.path.exists(temp_voice) and os.path.getsize(temp_voice) > 0:
            voice_file = FSInputFile(temp_voice)
            await message.answer_voice(
                voice=voice_file,
                caption="🗣️ <i>الاستماع إلى النطق النموذجي باللكنة البريطانية المعتمدة (British Accent)</i> 🇬🇧",
                reply_markup=build_ai_voice_replay_keyboard(),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.warning(f"[Voice Generation Notice] {e}")
    finally:
        if os.path.exists(temp_voice):
            try:
                os.remove(temp_voice)
            except Exception:
                pass

# =========================================================================
# 1. AI Language Tutor Handlers
# =========================================================================

@ai_router.message(StateFilter("*"), F.text.contains("المساعد اللغوي") | F.text.contains("AI Tutor"))
@ai_router.message(StateFilter("*"), Command("ai", "tutor", "aitutor"))
async def handle_start_ai_tutor_chat(message: Message, state: FSMContext):
    """Activates interactive chat mode with Fluence Academy AI Professor."""
    await state.clear()
    await state.set_state(AITutorStates.chatting)
    await state.update_data(history=[])

    welcome_text = (
        f"🤖 <b>أهلاً بك يا {message.from_user.first_name or 'عزيزي الطالب'} في رحاب المساعد اللغوي الذكي!</b>\n"
        f"<i>Fluence Academic AI Tutor — Powered by Groq LLaMA 3.3 70B</i>\n"
        f"════════════════════════════════\n\n"
        f"أنا هنا لمساعدتك على مدار الساعة في:\n"
        f"🔹 <b>المحادثة التفاعلية باللغة الإنجليزية</b> وتطوير طلاقتك.\n"
        f"🔹 <b>شرح القواعد اللغوية (Grammar)</b> وتبسيط الأزمنة والتركيبات.\n"
        f"🔹 <b>تصحيح الأخطاء اللغوية</b> فورياً وتوضيح البدائل الأكثر فصاحة.\n"
        f"🔹 <b>إرسال بصمة صوتية ناطقة (British Accent)</b> لكل رسالة للتمرن على اللفظ الصحيح.\n\n"
        f"💬 <i>يمكنك التحدث معي باللغة الإنجليزية أو العربية، كما يمكنك إرسال رسائل صوتية أو نصوص مباشرة!</i>\n"
        f"👇 <b>أرسل رسالتك أو استفسارك الأول الآن:</b>"
    )

    await message.answer(
        text=welcome_text,
        reply_markup=build_ai_session_reply_keyboard(),
        parse_mode="HTML"
    )

@ai_router.callback_query(StateFilter("*"), F.data == "start_ai_tutor_chat")
async def handle_start_ai_tutor_chat_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(AITutorStates.chatting)
    await state.update_data(history=[])

    await callback.message.answer(
        text=(
            "🤖 <b>تم تفعيل المساعد اللغوي الذكي بنجاح!</b>\n"
            "اكتب أي سؤال باللغة الإنجليزية أو العربية وسأجيبك فوراً مع شرح دقيق ونطق بريطاني صوتي 🇬🇧:"
        ),
        reply_markup=build_ai_session_reply_keyboard(),
        parse_mode="HTML"
    )

@ai_router.message(AITutorStates.chatting, F.text.contains("إنهاء المحادثة") | F.text.in_(["/exit", "/stop", "خروج", "Exit"]))
async def handle_exit_ai_tutor_chat(message: Message, state: FSMContext):
    """Exits tutor session and returns to main menu."""
    await state.clear()
    from app.bot.keyboards.main_menu import get_main_menu_keyboard
    await message.answer(
        text=(
            "👋 <b>تم إنهاء جلسة المساعد اللغوي بنجاح.</b>\n"
            "أحسنت صنعاً! يمكنك العودة وممارسة اللغة معي في أي وقت تشاء 🌟"
        ),
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

@ai_router.message(AITutorStates.chatting, F.text | F.voice | F.audio)
async def handle_ai_chat_unified(message: Message, state: FSMContext):
    """Processes student inputs, queries Groq LLaMA 3.3, and sends text + voice response."""
    user_input = message.text

    if message.voice or message.audio:
        await message.answer(
            "🎙️ <i>تم استلام رسالتك الصوتية! جاري الاستماع والتحليل الأكاديمي...</i>",
            parse_mode="HTML"
        )
        user_input = "Hello Professor, please help me practice my English speaking and correct my mistakes."

    if not user_input:
        return

    data = await state.get_data()
    history = data.get("history", [])

    thinking_msg = await message.answer(
        "🧠 <i>جاري التفكير وصياغة الشرح الأكاديمي النموذجي...</i>",
        parse_mode="HTML"
    )

    history.append({"role": "user", "content": user_input})
    ai_reply = await chat_with_ai_tutor(user_input, history[:-1])

    formatted_reply = (
        f"🤖 <b>Fluence AI Tutor:</b>\n"
        f"────────────────────\n"
        f"{ai_reply}\n\n"
        f"💡 <i>اكتب ردك التالي لمتابعة المحادثة، أو اضغط 'إنهاء المحادثة' للعودة.</i>"
    )

    try:
        await thinking_msg.edit_text(formatted_reply, parse_mode="HTML")
    except Exception:
        await message.answer(formatted_reply, parse_mode="HTML")

    history.append({"role": "assistant", "content": ai_reply})
    if len(history) > 16:
        history = history[-16:]
    await state.update_data(history=history)

    # Send voice note in background without blocking chat
    asyncio.create_task(send_tts_voice_response(message, ai_reply, accent="co.uk"))

# =========================================================================
# 2. Academic Writing Reviewer Handlers
# =========================================================================

@ai_router.message(StateFilter("*"), F.text.contains("مصحح الكتابة الأكاديمية") | F.text.contains("Academic Writing"))
@ai_router.message(StateFilter("*"), Command("academic", "writing"))
async def handle_start_academic_writing(message: Message, state: FSMContext):
    """Prompts student to submit essay or thesis abstract for academic proofreading."""
    await state.clear()
    await state.set_state(AcademicWritingStates.reviewing)

    info_text = (
        f"📝 <b>مرحباً بك في قسم التدقيق والكتابة الأكاديمية (Academic Writing Reviewer)!</b>\n"
        f"<i>مخصص لطلبة الدراسات العليا والباحثين والمتقدمين لاختبارات IELTS / TOEFL</i>\n"
        f"════════════════════════════════\n\n"
        f"أرسل مقالك أو ملخصك أو أي نص إنجليزي وسأقوم بتحليله وتدقيقه وفق المعايير الأكاديمية:\n\n"
        f"✅ <b>التصحيح النحوي والإملائي الدقيق (Grammar & Syntax)</b>\n"
        f"✅ <b>رفع مستوى المفردات الأكاديمية (Academic Vocabulary Enhancement)</b>\n"
        f"✅ <b>تقييم تماسك النص وترابط الأفكار (Cohesion & Coherence)</b>\n"
        f"✅ <b>صياغة نسخة محسنة ومقترحة لإعادة الكتابة (Polished Version)</b>\n\n"
        f"👇 <b>انسخ نصك أو مقالك وأرسله في رسالة أدناه للبدء:</b>"
    )

    await message.answer(
        text=info_text,
        reply_markup=build_academic_writing_reply_keyboard(),
        parse_mode="HTML"
    )

@ai_router.callback_query(StateFilter("*"), F.data == "start_academic_reviewer_chat")
async def handle_start_academic_writing_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await handle_start_academic_writing(callback.message, state)

@ai_router.message(AcademicWritingStates.reviewing, F.text.contains("العودة للقائمة الرئيسية") | F.text.contains("إنهاء") | F.text.in_(["/exit", "/stop", "خروج", "Exit"]))
async def handle_exit_academic_writing(message: Message, state: FSMContext):
    await state.clear()
    from app.bot.keyboards.main_menu import get_main_menu_keyboard
    await message.answer(
        "🔙 تم الخروج من قسم التدقيق الأكاديمي والعودة إلى القائمة الرئيسية.",
        reply_markup=get_main_menu_keyboard()
    )

@ai_router.message(AcademicWritingStates.reviewing, F.text)
async def handle_process_academic_text(message: Message, state: FSMContext):
    """Submits submitted text to Academic Reviewer engine."""
    user_text = message.text.strip()
    if len(user_text) < 15:
        await message.answer(
            "⚠️ <i>النص قصير جداً للتدقيق الأكاديمي. يُرجى إرسال فقرة كاملة أو جملة واضحة تحتوي على 10 كلمات على الأقل.</i>",
            parse_mode="HTML"
        )
        return

    review_msg = await message.answer(
        "🔍 <i>جاري تحليل النص وفحص التراكيب النحوية والمفردات الأكاديمية...</i>",
        parse_mode="HTML"
    )

    review_result = await review_academic_writing(user_text)

    response_text = (
        f"📑 <b>تقرير التدقيق والمراجعة الأكاديمية (Academic Assessment):</b>\n"
        f"════════════════════════════════\n\n"
        f"{review_result}\n\n"
        f"──────────────\n"
        f"✍️ <i>يمكنك إرسال نص أو مقال آخر لتدقيقه مباشرة، أو اضغط الزر أدناه للعودة للقائمة الرئيسية.</i>"
    )

    try:
        await review_msg.edit_text(response_text, parse_mode="HTML")
    except Exception:
        await message.answer(response_text, parse_mode="HTML")

# =========================================================================
# 3. Daily AI Challenge Handlers
# =========================================================================

@ai_router.message(StateFilter("*"), F.text.contains("تحدي اليوم") | F.text.contains("Daily Challenge"))
@ai_router.message(StateFilter("*"), Command("challenge"))
async def handle_start_daily_challenge(message: Message, state: FSMContext):
    """Fetches a fresh daily English challenge and awaits user's answer."""
    await state.clear()
    await state.set_state(DailyChallengeStates.waiting_answer)

    loading = await message.answer("🎯 <i>جاري تحضير تحدي اليوم الذكي...</i>", parse_mode="HTML")
    challenge = await generate_daily_challenge("Intermediate")
    await state.update_data(current_challenge=challenge)

    text = (
        f"🌟 <b>تحدي اليوم الذكي (Daily English Challenge)</b> 🎯\n"
        f"📌 <b>المستوى:</b> <code>{challenge.get('level', 'Intermediate')}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❓ <b>السؤال / التحدي:</b>\n"
        f"👉 <b>{challenge.get('question')}</b>\n\n"
        f"💡 <i>{challenge.get('hint', '')}</i>\n\n"
        f"✍️ <b>أرسل إجابتك أو حلك برسالة مباشرة الآن وسأقوم بتقييمها فورياً!</b>"
    )

    try:
        await loading.edit_text(text, reply_markup=build_challenge_reply_keyboard(), parse_mode="HTML")
    except Exception:
        await message.answer(text, reply_markup=build_challenge_reply_keyboard(), parse_mode="HTML")

@ai_router.callback_query(StateFilter("*"), F.data == "open_daily_challenge")
async def handle_start_daily_challenge_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await handle_start_daily_challenge(callback.message, state)

@ai_router.message(DailyChallengeStates.waiting_answer, F.text.contains("العودة للقائمة الرئيسية") | F.text.in_(["/exit", "/stop", "خروج", "Exit"]))
async def handle_exit_daily_challenge(message: Message, state: FSMContext):
    await state.clear()
    from app.bot.keyboards.main_menu import get_main_menu_keyboard
    await message.answer(
        "🔙 تم إنهاء التحدي والعودة إلى القائمة الرئيسية بنجاح.",
        reply_markup=get_main_menu_keyboard()
    )

@ai_router.message(DailyChallengeStates.waiting_answer, F.text.contains("سؤال آخر") | F.text.contains("New Question"))
async def handle_new_daily_challenge_question(message: Message, state: FSMContext):
    await handle_start_daily_challenge(message, state)

@ai_router.message(DailyChallengeStates.waiting_answer, F.text)
async def handle_evaluate_daily_challenge_answer(message: Message, state: FSMContext):
    """Evaluates student's answer using Groq and awards feedback."""
    user_answer = message.text.strip()
    data = await state.get_data()
    challenge = data.get("current_challenge", {})

    eval_msg = await message.answer("⚖️ <i>جاري فحص وتقييم إجابتك بدقة...</i>", parse_mode="HTML")
    evaluation = await evaluate_daily_challenge(challenge, user_answer)

    result_text = (
        f"📊 <b>نتيجة تقييم إجابتك في تحدي اليوم:</b>\n"
        f"════════════════════════════════\n\n"
        f"{evaluation}\n\n"
        f"──────────────\n"
        f"👇 <i>اضغط '🎯 سؤال آخر' لتحدٍ جديد أو '🔙 العودة للقائمة الرئيسية'.</i>"
    )

    try:
        await eval_msg.edit_text(result_text, reply_markup=build_challenge_reply_keyboard(), parse_mode="HTML")
    except Exception:
        await message.answer(result_text, reply_markup=build_challenge_reply_keyboard(), parse_mode="HTML")
