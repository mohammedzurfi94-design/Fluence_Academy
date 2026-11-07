import asyncio
import os
import random
import requests
import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from datetime import datetime, timezone

from app.database.connection import AsyncSessionLocal
from app.database.models import User, Quiz, QuizQuestion, QuizAnswer, QuizAttempt, StudentProgress
from app.core.config import settings

quizzes_router = Router(name="quizzes_router")

try:
    from app.services.certificate_service import create_certificate_pdf
except Exception:
    create_certificate_pdf = None

try:
    from app.services.ai_service import get_today_lesson, send_daily_lesson_to_user
except Exception:
    def get_today_lesson(force_refresh=False):
        return {"topic": "Daily English", "info": "Welcome to Fluence Academy!", "questions": []}
    async def send_daily_lesson_to_user(bot, chat_id, lesson, send_voice=True):
        pass

def save_to_notion(first_name, username, score, level):
    url = "https://api.notion.com/v1/pages"
    token = os.getenv("NOTION_API_TOKEN") or getattr(settings, "NOTION_API_TOKEN", None) or "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"
    database_id = os.getenv("NOTION_DATABASE_ID") or getattr(settings, "NOTION_DATABASE_ID", None) or "7ae3e7572bf54b198a13816b43c90e05"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    username_text = f"@{username}" if username else "لا يوجد معرف"
    data = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": first_name or "طالب مجهول"}}]},
            "Username": {"rich_text": [{"text": {"content": username_text}}]},
            "Score": {"number": score},
            "Level": {"rich_text": [{"text": {"content": str(level)}}]}
        }
    }
    try:
        requests.post(url, headers=headers, json=data, timeout=10)
    except Exception as e:
        print(f"[Notion Error] {e}")

# ---------------------------------------------------------------------------
# بنك أسئلة اختبار تحديد المستوى المتجدد (20 سؤالاً CEFR)
# ---------------------------------------------------------------------------
PLACEMENT_QUESTION_BANK = {
    "A1": [
        {"question": "What ___ your name?", "correct_ans": "is", "distractors": ["are", "am", "be"]},
        {"question": "Where ___ you from?", "correct_ans": "are", "distractors": ["is", "am", "be"]},
        {"question": "She ___ two brothers and one sister.", "correct_ans": "has", "distractors": ["have", "having", "is"]},
        {"question": "I usually get up ___ 7 o'clock.", "correct_ans": "at", "distractors": ["on", "in", "to"]},
        {"question": "They ___ students at the university.", "correct_ans": "are", "distractors": ["is", "am", "be"]},
    ],
    "A2": [
        {"question": "Yesterday, we ___ to the central library.", "correct_ans": "went", "distractors": ["go", "gone", "going"]},
        {"question": "Look! The children ___ football in the garden.", "correct_ans": "are playing", "distractors": ["play", "played", "is playing"]},
        {"question": "This dictionary is ___ than that one.", "correct_ans": "more useful", "distractors": ["usefuler", "most useful", "as useful"]},
        {"question": "Have you ever ___ to London?", "correct_ans": "been", "distractors": ["be", "was", "went"]},
    ],
    "B1": [
        {"question": "If it ___ tomorrow, we will postpone the lecture.", "correct_ans": "rains", "distractors": ["will rain", "rained", "rain"]},
        {"question": "The monograph ___ by the professor last semester.", "correct_ans": "was written", "distractors": ["wrote", "is written", "has written"]},
        {"question": "I have lived in this city ___ ten years.", "correct_ans": "for", "distractors": ["since", "from", "during"]},
        {"question": "You ___ park your vehicle here; it is strictly prohibited.", "correct_ans": "mustn't", "distractors": ["don't have to", "needn't", "might not"]},
    ],
    "B2": [
        {"question": "If I had known about the conference, I ___.", "correct_ans": "would have attended", "distractors": ["would attend", "attended", "will attend"]},
        {"question": "You ___ have left your keys in the hall; it was locked all day.", "correct_ans": "couldn't", "distractors": ["mustn't", "shouldn't", "wouldn't"]},
        {"question": "The economy was on the ___ of collapse.", "correct_ans": "brink", "distractors": ["edge", "border", "boundary"]},
        {"question": "She succeeded ___ passing the challenging examination.", "correct_ans": "in", "distractors": ["on", "at", "with"]},
    ],
    "C1": [
        {"question": "Seldom ___ such an insightful analysis of literature.", "correct_ans": "have I read", "distractors": ["I have read", "I read", "did I read"]},
        {"question": "His explanation was completely ___, leaving everyone confused.", "correct_ans": "opaque", "distractors": ["lucid", "transparent", "candid"]},
        {"question": "Scarcely had she finished speaking ___ the audience applauded.", "correct_ans": "when", "distractors": ["than", "then", "as"]},
        {"question": "Under no circumstances ___ the examination hall before time.", "correct_ans": "should you leave", "distractors": ["you should leave", "you leave", "you will leave"]},
    ],
    "C2": [
        {"question": "The keynote address was filled with mere ___.", "correct_ans": "platitudes", "distractors": ["accolades", "truisms", "veracities"]},
        {"question": "Little ___ that his hypothesis would transform modern linguistics.", "correct_ans": "did he realize", "distractors": ["he realized", "he had realized", "he was realizing"]},
        {"question": "The institutional decline was precipitated by administrative ___.", "correct_ans": "ineptitude", "distractors": ["aptitude", "fortitude", "solicitude"]},
        {"question": "The professor's lecture was distinguished by remarkable ___ and depth.", "correct_ans": "erudition", "distractors": ["superficiality", "vacuity", "pedantry"]},
    ]
}

def sample_diagnostic_placement_questions() -> list:
    sampled = []
    tiers = [("A1", 3), ("A2", 3), ("B1", 4), ("B2", 4), ("C1", 3), ("C2", 3)]
    for level, count in tiers:
        pool = PLACEMENT_QUESTION_BANK.get(level, [])
        picked = random.sample(pool, min(count, len(pool)))
        for item in picked:
            options = [item["correct_ans"]] + list(item["distractors"])
            random.shuffle(options)
            correct_idx = options.index(item["correct_ans"])
            sampled.append({
                "question": item["question"],
                "options": options,
                "correct": correct_idx,
                "level": level
            })
    return sampled

def get_placement_level_info(score: int, total: int = 20) -> tuple[str, str]:
    if score <= 4:
        return "A1 (Beginner)", "level_a1"
    elif score <= 8:
        return "A2 (Elementary)", "level_a2"
    elif score <= 12:
        return "B1 (Intermediate)", "level_b1"
    elif score <= 16:
        return "B2 (Upper-Intermediate)", "level_b2"
    else:
        return "C1/C2 (Advanced & Mastery)", "level_c1"

def build_placement_question_keyboard(q_idx: int, score: int, options: list[str]) -> InlineKeyboardMarkup:
    keyboard = []
    for i, opt in enumerate(options):
        keyboard.append([
            InlineKeyboardButton(text=f"{chr(65+i)}) {opt}", callback_data=f"pt_{q_idx}_{i}_{score}")
        ])
    keyboard.append([InlineKeyboardButton(text="❌ إلغاء الاختبار | Cancel", callback_data="back_to_courses")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ---------------------------------------------------------------------------
# 1. مشغل اختبار المستوى (من القائمة السفلية ومن رسالة /start)
# ---------------------------------------------------------------------------
@quizzes_router.message(F.text.contains("اختبار المستوى") | F.text.contains("Placement Test") | F.text.contains("تحديد المستوى"))
async def handle_placement_test(message: Message):
    text = (
        "📝 <b>اختبار تحديد المستوى الأكاديمي المعتمد (متجدد آلياً)</b>\n"
        "المشرف العام: <b>Lect. Mohammed Hussein</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "يتكون الاختبار من <b>20 سؤالاً تشخيصياً</b> متدرج الصعوبة (من A1 حتى C2).\n"
        "• 🔄 <b>أسئلة متجددة آلياً:</b> لا يتكرر نفس النموذج لضمان قياس مستواك الحقيقي بدقة.\n"
        "• 🏛️ <b>توثيق رسمي:</b> تُحفظ النتيجة في قاعدة بيانات الأكاديمية على Notion فور انتهائك.\n"
        "• 🎓 <b>شهادة إلكترونية رسمية (PDF):</b> تُصدر وتحمل باسمك فوراً عند إتمام الاختبار!\n\n"
        "👇 <b>اضغط على الزر أدناه لبدء الاختبار الآن:</b>"
    )
    keyboard = [
        [InlineKeyboardButton(text="🚀 ابدأ اختبار المستوى الآن | Start Test", callback_data="start_placement_test")],
        [InlineKeyboardButton(text="📚 دليل الكورسات | Courses", callback_data="back_to_courses")]
    ]
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@quizzes_router.callback_query(F.data.in_(["start_placement_test", "retake_placement_test"]))
async def handle_start_placement_test(callback: CallbackQuery, state: FSMContext):
    questions = sample_diagnostic_placement_questions()
    await state.update_data(placement_questions=questions)

    first_q = questions[0]
    total_q = len(questions)
    text = (
        f"📝 <b>اختبار تحديد المستوى الأكاديمي (السؤال 1 من {total_q})</b>\n"
        f"المستوى المستهدف: <b>{first_q.get('level', 'General')}</b>\n\n"
        f"❓ <b>{first_q['question']}</b>"
    )
    keyboard = build_placement_question_keyboard(0, 0, first_q["options"])
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@quizzes_router.callback_query(F.data.startswith("pt_"))
async def handle_placement_test_answer(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    q_idx = int(parts[1])
    selected_opt = int(parts[2])
    score = int(parts[3])

    data = await state.get_data()
    questions = data.get("placement_questions")
    if not questions or q_idx >= len(questions):
        questions = sample_diagnostic_placement_questions()
        await state.update_data(placement_questions=questions)

    current_q = questions[q_idx]
    if selected_opt == current_q["correct"]:
        score += 1

    next_idx = q_idx + 1
    total_q = len(questions)

    if next_idx < total_q:
        next_q = questions[next_idx]
        text = (
            f"📝 <b>اختبار تحديد المستوى الأكاديمي (السؤال {next_idx + 1} من {total_q})</b>\n"
            f"المستوى المستهدف: <b>{next_q.get('level', 'General')}</b>\n\n"
            f"❓ <b>{next_q['question']}</b>"
        )
        keyboard = build_placement_question_keyboard(next_idx, score, next_q["options"])
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
    else:
        level_name, target_callback = get_placement_level_info(score, total_q)
        final_score = score
        user_level = level_name
        tg_user = callback.from_user
        raw_name = (tg_user.full_name or tg_user.username or "Student") if tg_user else "Student"

        # حفظ النتيجة في Notion
        if tg_user:
            try:
                save_to_notion(tg_user.first_name, tg_user.username, final_score, user_level)
            except Exception as e:
                print(f"[Notion Placement Error] {e}")

        # تسجيل المحاولة في قاعدة البيانات
        if tg_user:
            try:
                async with AsyncSessionLocal() as session:
                    u_query = select(User).where(User.telegram_id == tg_user.id)
                    u_res = await session.execute(u_query)
                    user = u_res.scalar_one_or_none()
                    if user:
                        attempt = QuizAttempt(
                            student_id=user.id,
                            quiz_id=1,
                            score_percentage=round((final_score / total_q) * 100, 1),
                            passed=(final_score >= 10),
                            started_at=datetime.now(timezone.utc),
                            completed_at=datetime.now(timezone.utc)
                        )
                        session.add(attempt)
                        await session.commit()
            except Exception as e:
                print(f"[Database Progress Error] {e}")

        result_text = (
            "🏆 <b>نتيجة اختبار تحديد المستوى المعتمد</b> 🎓\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>الطالب:</b> {html.escape(raw_name)}\n"
            f"📊 <b>النتيجة المحققة:</b> {final_score} من {total_q} أسئلة ({round((final_score/total_q)*100)}%)\n"
            f"🏅 <b>المستوى اللغوي (CEFR):</b>\n👉 <b>{user_level}</b>\n\n"
            "🏛️ <b>تم توثيق نتيجتك رسمياً في قاعدة بيانات أكاديمية Fluence على Notion.</b>\n"
            "📜 <i>تم توليد وإصدار شهادتك الرسمية المعتمدة بصيغة PDF وتجدها مرفقة أدناه:</i>"
        )

        result_keyboard = [
            [InlineKeyboardButton(text="🎓 تحميل شهادتي الرسمية المعتمدة (PDF)", callback_data=f"download_cert_{final_score}_{total_q}")],
            [InlineKeyboardButton(text="📖 تصفح كورس مستواي الموصى به", callback_data=target_callback)],
            [InlineKeyboardButton(text="🔄 إعادة الاختبار بنموذج جديد", callback_data="start_placement_test")],
            [InlineKeyboardButton(text="🏠 القائمة الرئيسية | Main Menu", callback_data="back_to_main_menu")]
        ]

        await state.clear()
        try:
            await callback.message.edit_text(result_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=result_keyboard), parse_mode="HTML")
        except Exception:
            await callback.message.answer(result_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=result_keyboard), parse_mode="HTML")
        await callback.answer()

        # إرسال الشهادة تلقائياً للطالب
        if tg_user and create_certificate_pdf:
            try:
                cert_id = f"FA-CEFR-{datetime.now().year}-{tg_user.id % 10000:04d}"
                today_date = datetime.now().strftime("%Y-%m-%d")
                latin_chars = "".join(c for c in raw_name if (65 <= ord(c) <= 90 or 97 <= ord(c) <= 122 or c == " ")).strip()
                student_display_name = latin_chars if len(latin_chars) >= 3 else (f"Scholar @{tg_user.username}" if tg_user.username else "Fluence Academy Scholar")

                storage_dir = "storage/certificates"
                os.makedirs(storage_dir, exist_ok=True)
                cert_filename = f"Certificate_{tg_user.id}_{int(datetime.now().timestamp())}.pdf"
                cert_path = os.path.join(storage_dir, cert_filename)

                await asyncio.to_thread(
                    create_certificate_pdf,
                    student_name=student_display_name,
                    score=final_score,
                    total_questions=total_q,
                    level=user_level,
                    cert_id=cert_id,
                    issue_date=today_date,
                    output_path=cert_path
                )

                if os.path.exists(cert_path) and os.path.getsize(cert_path) > 0:
                    doc = FSInputFile(cert_path, filename=f"Fluence_Certificate_{cert_id}.pdf")
                    caption = (
                        "🎓 <b>تهانينا الحارة! إليك شهادتك الرسمية المعتمدة من أكاديمية Fluence</b> 🌟\n"
                        "═══════════════════════════════\n"
                        f"👤 <b>اسم الطالب:</b> {html.escape(raw_name)}\n"
                        f"📊 <b>الدرجة المحققة:</b> {final_score} من {total_q} ({round((final_score/total_q)*100, 1)}%)\n"
                        f"🏆 <b>المستوى الأكاديمي (CEFR):</b> {user_level}\n"
                        f"🆔 <b>رقم الاعتماد:</b> <code>{cert_id}</code>\n"
                        f"✍️ <b>المشرف العام:</b> Lect. Mohammed Hussein\n\n"
                        "<i>تم توثيق وحفظ الشهادة رسمياً في قاعدة بيانات الأكاديمية. يمكنك تحميلها وطباعتها الآن! ✨</i>"
                    )
                    try:
                        await callback.message.answer_document(document=doc, caption=caption, parse_mode="HTML")
                    except Exception:
                        if callback.bot and tg_user:
                            await callback.bot.send_document(chat_id=tg_user.id, document=doc, caption=caption, parse_mode="HTML")
            except Exception as cert_err:
                print(f"[Auto Certificate Notice] {cert_err}")

# ---------------------------------------------------------------------------
# 2. تحميل الشهادة عند الضغط على زر التحميل المباشر
# ---------------------------------------------------------------------------
@quizzes_router.callback_query(F.data.startswith("download_cert_"))
async def handle_download_cert_callback(callback: CallbackQuery):
    try:
        await callback.answer("🎓 جاري إعداد وتصدير شهادتك الرسمية المعتمدة...")
    except Exception:
        pass

    parts = callback.data.split("_")
    score = int(parts[2]) if len(parts) > 2 else 10
    total_q = int(parts[3]) if len(parts) > 3 else 20

    level_name, _ = get_placement_level_info(score, total_q)
    tg_user = callback.from_user
    raw_name = (tg_user.full_name or tg_user.username or "Student") if tg_user else "Student"
    latin_chars = "".join(c for c in raw_name if (65 <= ord(c) <= 90 or 97 <= ord(c) <= 122 or c == " ")).strip()
    student_display_name = latin_chars if len(latin_chars) >= 3 else (f"Scholar @{tg_user.username}" if tg_user and tg_user.username else "Fluence Academy Scholar")

    cert_id = f"FA-CEFR-{datetime.now().year}-{(tg_user.id if tg_user else 1000) % 10000:04d}"
    today_date = datetime.now().strftime("%Y-%m-%d")

    storage_dir = "storage/certificates"
    os.makedirs(storage_dir, exist_ok=True)
    cert_path = os.path.join(storage_dir, f"Certificate_{tg_user.id if tg_user else 0}_{int(datetime.now().timestamp())}.pdf")

    try:
        if create_certificate_pdf:
            await asyncio.to_thread(
                create_certificate_pdf,
                student_name=student_display_name,
                score=score,
                total_questions=total_q,
                level=level_name,
                cert_id=cert_id,
                issue_date=today_date,
                output_path=cert_path
            )

        if os.path.exists(cert_path) and os.path.getsize(cert_path) > 0:
            doc = FSInputFile(cert_path, filename=f"Fluence_Certificate_{cert_id}.pdf")
            caption = (
                "🎓 <b>نسخة شهادتك الرسمية المعتمدة | Official Certificate</b>\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                f"الطالب: <b>{html.escape(raw_name)}</b>\n"
                f"المستوى المحقق: <b>{level_name}</b> ({score}/{total_q})\n"
                f"المشرف العام: <b>Lect. Mohammed Hussein</b>\n"
                f"رقم التوثيق: <code>{cert_id}</code>"
            )
            try:
                await callback.message.answer_document(document=doc, caption=caption, parse_mode="HTML")
            except Exception:
                if callback.bot and tg_user:
                    await callback.bot.send_document(chat_id=tg_user.id, document=doc, caption=caption, parse_mode="HTML")
        else:
            await callback.answer("⚠️ تعذر إنشاء الشهادة حالياً، يرجى المحاولة بعد قليل.", show_alert=True)
    except Exception as e:
        print(f"[Certificate Download Error] {e}")
        await callback.message.answer("⚠️ حدث تأخر مؤقت في إصدار ملف الشهادة. يرجى المحاولة مرة أخرى.")

# ---------------------------------------------------------------------------
# 3. قسم الاختبارات اليومية وسجل درجات الطالب (من القائمة السفلية)
# ---------------------------------------------------------------------------
@quizzes_router.message(F.text.contains("الاختبارات اليومية") | F.text.contains("Quizzes"))
async def handle_quizzes_and_grades(message: Message):
    tg_user = message.from_user
    if not tg_user:
        return

    async with AsyncSessionLocal() as session:
        u_query = select(User).where(User.telegram_id == tg_user.id)
        u_result = await session.execute(u_query)
        user = u_result.scalar_one_or_none()

        if not user:
            await message.answer("⚠️ يرجى كتابة /start أولاً لتفعيل حسابك الأكاديمي.")
            return

        try:
            att_query = select(QuizAttempt).where(QuizAttempt.student_id == user.id).order_by(QuizAttempt.completed_at.desc())
            att_result = await session.execute(att_query)
            attempts = att_result.scalars().all()
        except Exception as e:
            print(f"[Attempts Query Notice] {e}")
            attempts = []

        try:
            quizzes_q = select(Quiz).limit(5)
            quizzes_res = await session.execute(quizzes_q)
            available_quizzes = quizzes_res.scalars().all()
        except Exception:
            available_quizzes = []

    text = f"🎯 <b>قسم الاختبارات والتقييم اليومي | Quizzes & Grades</b>\n\n"
    text += f"👤 <b>الطالب:</b> {user.full_name}\n"

    if attempts:
        text += f"📊 <b>نتائج آخر الاختبارات المنجزة:</b>\n"
        for att in attempts[:5]:
            badge = "✅ ناجح" if att.passed else "❌ تدرب أكثر"
            text += f"• اختبار #{att.quiz_id}: النتيجة <b>{att.score_percentage}%</b> ({badge})\n"
        text += "\n"
    else:
        text += "لم تقم بأداء أي اختبارات بعد. ابدأ الآن بتحدي معلوماتك اليومية! 🚀\n\n"

    keyboard = [
        [InlineKeyboardButton(text="💡 معلومة اليوم واختبارها (متجددة آلياً 🎙️)", callback_data="open_daily_info")],
        [InlineKeyboardButton(text="🔄 اختبار ذكي متجدد (AI Quiz Generator)", callback_data="refresh_daily_lesson")],
    ]

    if available_quizzes:
        keyboard.append([InlineKeyboardButton(text="─── 📚 اختبارات الدروس والكورسات ───", callback_data="ignore_header")])
        for q in available_quizzes:
            keyboard.append([InlineKeyboardButton(text=f"✍️ {q.title}", callback_data=f"start_quiz_{q.lesson_id or q.id}")])

    keyboard.append([InlineKeyboardButton(text="📚 الانتقال للدورات | Courses", callback_data="back_to_courses")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@quizzes_router.callback_query(F.data == "ignore_header")
async def handle_ignore_header(callback: CallbackQuery):
    await callback.answer()

@quizzes_router.callback_query(F.data.in_(["back_to_quizzes_menu", "open_quizzes_hub"]))
async def handle_back_to_quizzes_menu(callback: CallbackQuery):
    await callback.answer()
    if callback.message:
        await handle_quizzes_and_grades(callback.message)

# ---------------------------------------------------------------------------
# 4. كبسولة معلومة اليوم الصوتية باللكنة البريطانية (Daily Info & Voice)
# ---------------------------------------------------------------------------
@quizzes_router.callback_query(F.data == "open_daily_info")
async def handle_open_daily_info(callback: CallbackQuery):
    await callback.answer("جاري تجهيز معلومة اليوم واختبارها...")
    lesson = get_today_lesson(force_refresh=False)
    await send_daily_lesson_to_user(callback.bot, callback.message.chat.id, lesson, send_voice=True)

@quizzes_router.callback_query(F.data == "refresh_daily_lesson")
async def handle_refresh_daily_lesson(callback: CallbackQuery):
    await callback.answer("🔄 جاري توليد معلومة واختبار جديد بالذكاء الاصطناعي...")
    await callback.message.answer(
        "⚡ <b>جاري إعداد محتوى تعليمي واختبار جديد بالذكاء الاصطناعي...</b>\n<i>ثوانٍ معدودة...</i>",
        parse_mode="HTML"
    )
    lesson = await asyncio.to_thread(get_today_lesson, force_refresh=True)
    await send_daily_lesson_to_user(callback.bot, callback.message.chat.id, lesson, send_voice=True)

# ---------------------------------------------------------------------------
# 5. اختبار فهم معلومة اليوم وتصحيحها الفوري (Daily Info Quiz)
# ---------------------------------------------------------------------------
@quizzes_router.callback_query(F.data == "start_daily_info_quiz")
async def handle_start_daily_info_quiz(callback: CallbackQuery):
    lesson = get_today_lesson(force_refresh=False)
    questions = lesson.get("questions", [])

    if not questions:
        await callback.answer("عذراً، الأسئلة قيد التجهيز.", show_alert=True)
        return

    first_q = questions[0]
    total_q = len(questions)

    text = (
        f"📝 <b>اختبار معلومة اليوم: {lesson.get('topic', 'English Lesson')}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>السؤال 1 من {total_q}:</b>\n\n"
        f"❓ {first_q['question']}"
    )

    keyboard = []
    for opt_idx, opt_text in enumerate(first_q.get("options", [])):
        keyboard.append([
            InlineKeyboardButton(text=opt_text, callback_data=f"dquiz_0_{opt_idx}_0")
        ])

    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@quizzes_router.callback_query(F.data.startswith("dquiz_"))
async def handle_daily_quiz_answer(callback: CallbackQuery):
    parts = callback.data.split("_")
    q_idx = int(parts[1])
    selected_opt = int(parts[2])
    current_score = int(parts[3])

    lesson = get_today_lesson(force_refresh=False)
    questions = lesson.get("questions", [])

    if q_idx >= len(questions):
        await callback.answer("انتهى الاختبار.", show_alert=True)
        return

    current_q = questions[q_idx]
    correct_idx = current_q.get("correct_index", 0)
    is_correct = (selected_opt == correct_idx)
    explanation = current_q.get("explanation", "")

    if is_correct:
        current_score += 1
        feedback = "✅ <b>إجابة صحيحة! (Correct!)</b>"
    else:
        correct_answer_text = current_q["options"][correct_idx] if correct_idx < len(current_q["options"]) else ""
        feedback = f"❌ <b>إجابة خاطئة! (Incorrect)</b>\nالجواب الصحيح: <b>«{correct_answer_text}»</b>"

    if explanation:
        feedback += f"\n<i>💡 التوضيح: {explanation}</i>"

    next_q_idx = q_idx + 1
    total_q = len(questions)

    if next_q_idx < total_q:
        next_q = questions[next_q_idx]
        text = (
            f"{feedback}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>السؤال {next_q_idx + 1} من {total_q}:</b>\n\n"
            f"❓ {next_q['question']}"
        )
        keyboard = []
        for opt_idx, opt_text in enumerate(next_q.get("options", [])):
            keyboard.append([
                InlineKeyboardButton(text=opt_text, callback_data=f"dquiz_{next_q_idx}_{opt_idx}_{current_score}")
            ])

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    else:
        percentage = round((current_score / total_q) * 100, 1)
        passed = percentage >= 70.0

        if passed:
            result_header = "🎉 <b>أحسنت صنعاً! اجتزت اختبار المعلومة بنجاح</b> 🌟"
            status_text = "النتيجة: <b>ناجح ومتميز ✅</b>"
        else:
            result_header = "📚 <b>تدريب جيد! راجع المعلومة وحاول مجدداً</b>"
            status_text = "النتيجة: <b>تحتاج لمراجعة إضافية ❌</b>"

        final_text = (
            f"{feedback}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{result_header}\n\n"
            f"📌 <b>الموضوع:</b> {lesson.get('topic')}\n"
            f"📊 <b>درجتك:</b> {current_score} من {total_q} ({percentage}%)\n"
            f"{status_text}\n\n"
            f"✨ <i>يتم تحديث معلومات وأسئلة الأكاديمية يومياً وفق جدول دراسي منتظم!</i>"
        )

        keyboard = [
            [InlineKeyboardButton(text="🔄 معلومة واختبار آخر", callback_data="refresh_daily_lesson")],
            [InlineKeyboardButton(text="🔙 العودة لقسم الاختبارات", callback_data="back_to_quizzes_menu")],
            [InlineKeyboardButton(text="📚 الدورات الأكاديمية", callback_data="back_to_courses")]
        ]

        await callback.message.edit_text(final_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

    await callback.answer()

# ---------------------------------------------------------------------------
# 6. اختبارات الدروس والكورسات العادية (Lesson Quizzes)
# ---------------------------------------------------------------------------
@quizzes_router.callback_query(F.data.startswith("start_quiz_"))
async def handle_start_quiz(callback: CallbackQuery):
    lesson_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        q_query = select(Quiz).where(Quiz.lesson_id == lesson_id)
        q_result = await session.execute(q_query)
        quiz = q_result.scalar_one_or_none()

        if not quiz:
            await callback.answer("No quiz available for this lesson yet.", show_alert=True)
            return

        quest_query = select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.order_index)
        quest_result = await session.execute(quest_query)
        questions = quest_result.scalars().all()

        if not questions:
            await callback.answer("Quiz questions are being prepared.", show_alert=True)
            return

        first_q = questions[0]
        ans_query = select(QuizAnswer).where(QuizAnswer.question_id == first_q.id)
        ans_result = await session.execute(ans_query)
        answers = ans_result.scalars().all()

        keyboard = []
        for ans in answers:
            keyboard.append([
                InlineKeyboardButton(text=ans.answer_text, callback_data=f"ans_{quiz.id}_{first_q.id}_{ans.id}_0_0")
            ])

        card_text = (
            f"🧠 <b>اختبار الدرس: {quiz.title}</b>\n\n"
            f"❓ <b>السؤال 1 من {len(questions)}:</b>\n"
            f"{first_q.question_text}"
        )
        try:
            await callback.message.edit_text(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        except Exception:
            await callback.message.answer(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        await callback.answer()

@quizzes_router.callback_query(F.data.startswith("ans_"))
async def handle_answer_selected(callback: CallbackQuery):
    parts = callback.data.split("_")
    quiz_id = int(parts[1])
    current_q_id = int(parts[2])
    chosen_ans_id = int(parts[3])
    q_index = int(parts[4])
    current_score = int(parts[5])

    async with AsyncSessionLocal() as session:
        ans_query = select(QuizAnswer).where(QuizAnswer.id == chosen_ans_id)
        ans_result = await session.execute(ans_query)
        selected_answer = ans_result.scalar_one_or_none()

        is_correct = selected_answer.is_correct if selected_answer else False
        new_score = current_score + (1 if is_correct else 0)

        quest_query = select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.order_index)
        quest_result = await session.execute(quest_query)
        questions = quest_result.scalars().all()

        next_index = q_index + 1
        if next_index < len(questions):
            next_q = questions[next_index]
            n_ans_query = select(QuizAnswer).where(QuizAnswer.question_id == next_q.id)
            n_ans_result = await session.execute(n_ans_query)
            next_answers = n_ans_result.scalars().all()

            keyboard = []
            for ans in next_answers:
                keyboard.append([
                    InlineKeyboardButton(text=ans.answer_text, callback_data=f"ans_{quiz_id}_{next_q.id}_{ans.id}_{next_index}_{new_score}")
                ])

            feedback = "✅ <b>إجابة صحيحة وممتازة!</b>" if is_correct else "❌ <b>إجابة غير صحيحة، ركز في القادم!</b>"
            card_text = (
                f"{feedback}\n\n"
                f"❓ <b>السؤال {next_index + 1} من {len(questions)}:</b>\n"
                f"{next_q.question_text}"
            )
            try:
                await callback.message.edit_text(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
            except Exception:
                await callback.message.answer(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
            await callback.answer()
        else:
            total_questions = len(questions)
            percentage = round((new_score / total_questions) * 100) if total_questions > 0 else 0
            tg_user = callback.from_user

            if tg_user:
                u_query = select(User).where(User.telegram_id == tg_user.id)
                u_res = await session.execute(u_query)
                user = u_res.scalar_one_or_none()

                if user:
                    attempt = QuizAttempt(
                        student_id=user.id,
                        quiz_id=quiz_id,
                        score_percentage=percentage,
                        passed=(percentage >= 70),
                        started_at=datetime.now(timezone.utc),
                        completed_at=datetime.now(timezone.utc)
                    )
                    session.add(attempt)
                    await session.commit()

            result_keyboard = [
                [InlineKeyboardButton(text="🔙 العودة للدروس | Back to Courses", callback_data="back_to_courses")],
                [InlineKeyboardButton(text="🏠 القائمة الرئيسية | Main Menu", callback_data="back_to_main_menu")]
            ]

            result_text = (
                f"🎉 <b>اكتمل الاختبار بنجاح!</b>\n\n"
                f"📊 <b>نتيجتك النهائية:</b> {new_score} من {total_questions} ({percentage}%)\n\n"
                f"{'🏆 <b>أداء رائع ومبهر! لقد اجتزت الاختبار بنجاح.</b>' if percentage >= 70 else '💪 <b>حاول مجدداً وراجع الدرس لتحقيق نتيجة أعلى!</b>'}"
            )

            try:
                await callback.message.edit_text(result_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=result_keyboard), parse_mode="HTML")
            except Exception:
                await callback.message.answer(result_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=result_keyboard), parse_mode="HTML")
            await callback.answer()
