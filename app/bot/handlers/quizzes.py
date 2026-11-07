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

# 1. Initialize quizzes_router immediately at the top level
quizzes_router = Router(name="quizzes_router")

try:
    from app.services.ai_service import get_today_lesson, send_daily_lesson_to_user
except Exception:
    try:
        from app.services.scheduler_service import get_today_lesson, send_daily_lesson_to_user
    except Exception:
        def get_today_lesson(force_refresh=False):
            return {
                "topic": "Daily English",
                "info": "Welcome to Fluence Academy!",
                "questions": []
            }
        async def send_daily_lesson_to_user(bot, chat_id, lesson, send_voice=True):
            pass

# --- محرك توليد الشهادات الإلكترونية الرسمية المعتمدة (100% Pure Python & Self-Contained) ---
def create_certificate_pdf(
    student_name: str,
    score: int,
    total_questions: int,
    level: str,
    cert_id: str,
    issue_date: str,
    output_path: str
) -> str:
    """Creates strictly valid Landscape A4 PDF certificate with embedded logo."""
    percentage = round((score / total_questions) * 100, 1) if total_questions > 0 else 0

    clean_name = ''.join(c for c in str(student_name) if 32 <= ord(c) <= 126).strip() or "Fluence Scholar"
    clean_level = ''.join(c for c in str(level) if 32 <= ord(c) <= 126).strip().upper() or "B2"
    clean_id = ''.join(c for c in str(cert_id) if 32 <= ord(c) <= 126).strip() or "FA-CEFR-2026-0001"
    clean_date = ''.join(c for c in str(issue_date) if 32 <= ord(c) <= 126).strip() or datetime.now().strftime("%Y-%m-%d")

    logo_candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "logo_square.jpg"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "logo.jpg"),
        os.path.join("app", "assets", "logo_square.jpg"),
        os.path.join("app", "assets", "logo.jpg"),
        "logo_square.jpg",
        "logo.jpg"
    ]
    logo_bytes = None
    for cand in logo_candidates:
        if os.path.exists(cand):
            try:
                with open(cand, 'rb') as lf:
                    logo_bytes = lf.read()
                break
            except Exception:
                pass

    stream_ops = []
    # الخلفية البيضاء
    stream_ops.append('1 1 1 rg 0 0 842 595 re f')
    # الإطارات الملكية (كحلي وذهبي)
    stream_ops.append('0.06 0.13 0.28 RG 6 w 25 25 792 545 re S')
    stream_ops.append('0.79 0.65 0.27 RG 2 w 35 35 772 525 re S')
    stream_ops.append('0.06 0.13 0.28 RG 0.8 w 41 41 760 513 re S')
    stream_ops.append('0.79 0.65 0.27 rg 33 33 12 12 re f 797 33 12 12 re f 33 550 12 12 re f 797 550 12 12 re f')

    # الشعار الرسمي أعلى الشهادة
    if logo_bytes:
        stream_ops.append('q 64 0 0 64 389 488 cm /Im1 Do Q')

    # ترويسة الأكاديمية
    stream_ops.append('BT /F2 18 Tf 0.06 0.13 0.28 rg 290 460 Td (FLUENCE ENGLISH ACADEMY) Tj ET')
    stream_ops.append('BT /F4 10 Tf 0.79 0.65 0.27 rg 305 444 Td (ACCREDITED LANGUAGE & ACADEMIC PLATFORM) Tj ET')
    stream_ops.append('BT /F3 26 Tf 0.08 0.16 0.35 rg 215 395 Td (CERTIFICATE OF PROFICIENCY) Tj ET')
    stream_ops.append('BT /F4 11 Tf 0.45 0.50 0.58 rg 270 375 Td (COMMON EUROPEAN FRAMEWORK OF REFERENCE - CEFR) Tj ET')
    stream_ops.append('BT /F1 12 Tf 0.35 0.38 0.44 rg 355 335 Td (This is to certify that) Tj ET')

    # اسم الطالب المسجل
    name_x = max(100, int(421 - (len(clean_name) * 11 / 2)))
    stream_ops.append(f'BT /F2 22 Tf 0.08 0.16 0.35 rg {name_x} 300 Td ({clean_name}) Tj ET')
    stream_ops.append('0.79 0.65 0.27 RG 1.5 w 250 292 m 592 292 l S')

    # البيان الأكاديمي
    stream_ops.append('BT /F1 11.5 Tf 0.25 0.28 0.34 rg 170 262 Td (has successfully completed the comprehensive diagnostic English placement assessment) Tj ET')
    stream_ops.append('BT /F1 11.5 Tf 0.25 0.28 0.34 rg 210 244 Td (demonstrating proven academic competence and linguistic proficiency evaluated at:) Tj ET')

    # وسام المستوى المعتمد
    stream_ops.append('0.06 0.13 0.28 rg 271 185 300 42 re f')
    stream_ops.append('0.79 0.65 0.27 RG 2 w 271 185 300 42 re S')
    badge_text = f'CEFR LEVEL: {clean_level}'
    badge_x = int(421 - (len(badge_text) * 8.5 / 2))
    stream_ops.append(f'BT /F2 15 Tf 1 1 1 rg {badge_x} 200 Td ({badge_text}) Tj ET')

    score_text = f'Official Assessment Score: {score}/{total_questions} - {percentage}%'
    score_x = int(421 - (len(score_text) * 6.5 / 2))
    stream_ops.append(f'BT /F2 10.5 Tf 0.08 0.16 0.35 rg {score_x} 165 Td ({score_text}) Tj ET')

    # بيانات التوثيق والتحقق
    stream_ops.append('0.79 0.65 0.27 RG 1 w 70 148 m 260 148 l S')
    stream_ops.append(f'BT /F2 9.5 Tf 0.15 0.18 0.24 rg 70 133 Td (Credential ID: {clean_id}) Tj ET')
    stream_ops.append(f'BT /F1 9 Tf 0.30 0.35 0.42 rg 70 119 Td (Issue Date: {clean_date}) Tj ET')
    stream_ops.append('BT /F4 8 Tf 0.45 0.50 0.58 rg 70 105 Td (Verified in Fluence Academy Notion Registry) Tj ET')

    # ختم الأكاديمية بالأسفل
    if logo_bytes:
        stream_ops.append('q 60 0 0 60 391 80 cm /Im1 Do Q')

    # توقيع الأستاذ المشرف العام
    stream_ops.append('0.79 0.65 0.27 RG 1 w 580 148 m 770 148 l S')
    stream_ops.append('BT /F2 9.5 Tf 0.15 0.18 0.24 rg 580 133 Td (Lect. Mohammed Hussein) Tj ET')
    stream_ops.append('BT /F1 8.5 Tf 0.35 0.38 0.44 rg 580 119 Td (Director & General Academic Supervisor) Tj ET')
    stream_ops.append('BT /F4 8 Tf 0.45 0.50 0.58 rg 580 105 Td (Fluence English Academy) Tj ET')

    content = '\n'.join(stream_ops).encode('latin1')
    content_len = len(content)

    res_dict = b'<< /Font << /F1 4 0 R /F2 5 0 R /F3 6 0 R /F4 7 0 R >>'
    if logo_bytes:
        res_dict += b' /XObject << /Im1 9 0 R >>'
    res_dict += b' >>'

    header = b'%PDF-1.4\n'
    objs = [
        b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj',
        b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj',
        b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Resources ' + res_dict + b' /Contents 8 0 R >>\nendobj',
        b'4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj',
        b'5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj',
        b'6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold >>\nendobj',
        b'7 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Times-Italic >>\nendobj',
        f'8 0 obj\n<< /Length {content_len} >>\nstream\n'.encode('latin1') + content + b'\nendstream\nendobj'
    ]

    if logo_bytes:
        objs.append(
            f'9 0 obj\n<< /Type /XObject /Subtype /Image /Width 477 /Height 477 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(logo_bytes)} >>\nstream\n'.encode('latin1')
            + logo_bytes
            + b'\nendstream\nendobj'
        )

    raw = header
    offsets = []
    for obj in objs:
        offsets.append(len(raw))
        raw += obj + b'\n'

    xref_offset = len(raw)
    xref_str = f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'
    for off in offsets:
        xref_str += f'{off:010d} 00000 n \n'

    raw += xref_str.encode('latin1')
    raw += f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n'.encode('latin1')

    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with open(output_path, 'wb') as f:
        f.write(raw)

    return output_path

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
            "Name": {
                "title": [{"text": {"content": first_name or "طالب مجهول"}}]
            },
            "Username": {
                "rich_text": [{"text": {"content": username_text}}]
            },
            "Score": {
                "number": score
            },
            "Level": {
                "rich_text": [{"text": {"content": str(level)}}]
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code in [200, 201]:
            print(f"Notion Success: Saved placement result for {first_name} (Score: {score}/20, Level: {level})")
    except Exception as e:
        print(f"Failed to connect to Notion: {e}")

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
                InlineKeyboardButton(
                    text=ans.answer_text,
                    callback_data=f"ans_{quiz.id}_{first_q.id}_{ans.id}_0_0"
                )
            ])

        card_text = (
            f"🧠 <b>اختبار الدرس: {quiz.title}</b>\n\n"
            f"❓ <b>السؤال 1 من {len(questions)}:</b>\n"
            f"{first_q.question_text}"
        )

        try:
            await callback.message.edit_text(
                card_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                card_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="HTML"
            )
        await callback.answer()

@quizzes_router.callback_query(F.data.startswith("ans_"))
async def handle_quiz_answer(callback: CallbackQuery):
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
                    InlineKeyboardButton(
                        text=ans.answer_text,
                        callback_data=f"ans_{quiz_id}_{next_q.id}_{ans.id}_{next_index}_{new_score}"
                    )
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
                        user_id=user.id,
                        quiz_id=quiz_id,
                        score=percentage,
                        passed=(percentage >= 70)
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

# --- بنك أسئلة اختبار تحديد المستوى المتجدد (20 سؤالاً CEFR) ---
PLACEMENT_QUESTIONS_POOL = [
    # A1 Level
    [
        {"q": "A1: What _____ your name?", "opts": ["is", "are", "be", "am"], "c": 0, "exp": "مع الضمائر المفردة غير المتكلم نستخدم فعل الكينونة is."},
        {"q": "A1: Where _____ you from?", "opts": ["is", "am", "are", "be"], "c": 2, "exp": "مع الضمير you نستخدم دائماً are في السؤال والحاضر."},
        {"q": "A1: She _____ two brothers and a sister.", "opts": ["have", "has", "is", "having"], "c": 1, "exp": "مع الفاعل المفرد الغائب (She) نستخدم has."},
        {"q": "A1: I get up _____ 7 o'clock every morning.", "opts": ["on", "in", "at", "to"], "c": 2, "exp": "نستخدم حرف الجر at مع الساعات المحددة."}
    ],
    # A2 Level
    [
        {"q": "A2: Yesterday, we _____ to the national museum.", "opts": ["go", "went", "gone", "going"], "c": 1, "exp": "الدلالة الزمنية Yesterday تتطلب صيغة الماضي البسيط went."},
        {"q": "A2: Look! It _____ outside right now.", "opts": ["rains", "rained", "is raining", "rain"], "c": 2, "exp": "كلمة Look و right now تدل على المضارع المستمر (is raining)."},
        {"q": "A2: This laptop is _____ than the old one.", "opts": ["more cheap", "cheaper", "cheap", "cheapest"], "c": 1, "exp": "الصفات القصيرة تضاف لها er في المقارنة: cheaper than."},
        {"q": "A2: Have you ever _____ to London?", "opts": ["be", "been", "was", "went"], "c": 1, "exp": "في صيغة المضارع التام بعد have/has نستخدم التصريف الثالث been."}
    ],
    # B1 Level
    [
        {"q": "B1: If it _____ tomorrow, we will cancel the trip.", "opts": ["rains", "will rain", "rained", "is raining"], "c": 0, "exp": "في جملة الشرط الأولى (First Conditional) يكون فعل الشرط مضارعاً بسيطاً."},
        {"q": "B1: I've lived in this city _____ five years.", "opts": ["since", "for", "during", "from"], "c": 1, "exp": "نستخدم for مع المدة الزمنية المحسوبة (five years)."},
        {"q": "B1: The report _____ by the committee yesterday.", "opts": ["was written", "wrote", "is written", "had written"], "c": 0, "exp": "جملة مبني للمجهول في الماضي البسيط: was + V3."},
        {"q": "B1: You _____ smoke in this hospital; it is forbidden.", "opts": ["don't have to", "mustn't", "needn't", "might not"], "c": 1, "exp": "نستخدم mustn't للتعبير عن التحريم والمنع القانوني القاطع."}
    ],
    # B2 Level
    [
        {"q": "B2: If I _____ you, I would accept the scholarship.", "opts": ["was", "were", "am", "had been"], "c": 1, "exp": "في الحالة الشرطية الثانية لتقديم النصيحة نستخدم were مع كل الضمائر."},
        {"q": "B2: Despite _____ hard, he didn't score full marks.", "opts": ["he studied", "studying", "study", "of studying"], "c": 1, "exp": "حرف الجر Despite يتبعه دائماً Gerund (-ing) أو اسم."},
        {"q": "B2: She apologized _____ arriving late to the seminar.", "opts": ["for", "to", "about", "on"], "c": 0, "exp": "الفعل apologize يأخذ حرف الجر for مع الفعل المضاف له ing."},
        {"q": "B2: By the time the doctor arrived, the patient _____.", "opts": ["recovered", "had recovered", "has recovered", "was recovering"], "c": 1, "exp": "الحدث الأسبق في الماضي يوضع في زمن الماضي التام had + V3."}
    ],
    # C1/C2 Advanced Level
    [
        {"q": "C1: Hardly _____ the lecture hall when the fire alarm rang.", "opts": ["I had entered", "had I entered", "entered I", "I entered"], "c": 1, "exp": "ظروف النفي مثل Hardly تتطلب قلباً في ترتيب الجملة (Inversion: Had + Subject + V3)."},
        {"q": "C1: It is imperative that the candidate _____ on time.", "opts": ["be", "is", "was", "will be"], "c": 0, "exp": "صيغة الـ Subjunctive بعد صفات مثل imperative تستوجب الفعل في المصدر المجرد (be)."},
        {"q": "C2: The professor's argument was so _____ that no one refuted it.", "opts": ["cogent", "lucid", "ambiguous", "trivial"], "c": 0, "exp": "كلمة Cogent تعني حجة مقنعة ومفحمة لا يمكن دحضها بسهولة."},
        {"q": "C2: Under no circumstances _____ allowed to leave the premises.", "opts": ["are visitors", "visitors are", "were visitors", "have visitors"], "c": 0, "exp": "العبارة الشرطية السالبة Under no circumstances تفرض تقديم الفعل المساعد على الفاعل (Inversion)."}
    ]
]

def generate_placement_quiz_set():
    selected_questions = []
    for level_group in PLACEMENT_QUESTIONS_POOL:
        sample = random.sample(level_group, min(4, len(level_group)))
        selected_questions.extend(sample)
    return selected_questions

placement_sessions = {}

@quizzes_router.callback_query(F.data == "start_placement_test")
async def handle_start_placement(callback: CallbackQuery):
    user_id = callback.from_user.id
    questions = generate_placement_quiz_set()
    placement_sessions[user_id] = {
        "questions": questions,
        "current_index": 0,
        "score": 0,
        "answers_history": []
    }

    first_q = questions[0]
    keyboard = []
    for idx, opt in enumerate(first_q["opts"]):
        keyboard.append([
            InlineKeyboardButton(text=f"{chr(65+idx)}) {opt}", callback_data=f"plce_ans_{idx}")
        ])

    card_text = (
        f"📝 <b>اختبار تحديد المستوى الأكاديمي المعتمد | Placement Test</b>\n"
        f"المشرف العام: <b>Lect. Mohammed Hussein</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"❓ <b>السؤال 1 من {len(questions)}:</b>\n"
        f"<b>{first_q['q']}</b>\n\n"
        f"<i>اختر الإجابة الأدق والأصح لغوياً أدناه:</i>"
    )

    try:
        await callback.message.edit_text(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@quizzes_router.callback_query(F.data.startswith("plce_ans_"))
async def handle_placement_answer(callback: CallbackQuery):
    user_id = callback.from_user.id
    chosen_opt = int(callback.data.split("_")[-1])

    session = placement_sessions.get(user_id)
    if not session:
        await callback.answer("انتهت جلسة الاختبار الحالية، يرجى البدء من جديد.", show_alert=True)
        return

    questions = session["questions"]
    curr_idx = session["current_index"]
    current_q = questions[curr_idx]

    is_correct = (chosen_opt == current_q["c"])
    if is_correct:
        session["score"] += 1

    session["answers_history"].append({
        "q": current_q["q"],
        "correct": is_correct,
        "exp": current_q["exp"]
    })

    session["current_index"] += 1
    next_idx = session["current_index"]

    if next_idx < len(questions):
        next_q = questions[next_idx]
        keyboard = []
        for idx, opt in enumerate(next_q["opts"]):
            keyboard.append([
                InlineKeyboardButton(text=f"{chr(65+idx)}) {opt}", callback_data=f"plce_ans_{idx}")
            ])

        card_text = (
            f"📝 <b>اختبار تحديد المستوى الأكاديمي المعتمد</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"❓ <b>السؤال {next_idx + 1} من {len(questions)}:</b>\n"
            f"<b>{next_q['q']}</b>\n\n"
            f"<i>اختر الإجابة الصحيحة أدناه:</i>"
        )
        try:
            await callback.message.edit_text(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        except Exception:
            await callback.message.answer(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        await callback.answer()
    else:
        final_score = session["score"]
        total_q = len(questions)
        tg_user = callback.from_user

        if final_score <= 4:
            user_level = "A1 (Beginner)"
            rec_course = "كورس التأسيس الشامل للمبتدئين (A1 - Starter)"
        elif final_score <= 8:
            user_level = "A2 (Elementary)"
            rec_course = "كورس بناء الجمل والتراكيب اللغوية (A2 - Elementary)"
        elif final_score <= 12:
            user_level = "B1 (Intermediate)"
            rec_course = "كورس اللغة المتوسطة والمحادثة المتقدمة (B1 - Intermediate)"
        elif final_score <= 16:
            user_level = "B2 (Upper-Intermediate)"
            rec_course = "كورس الكتابة الأكاديمية والامتحان التنافسي (B2 - Competitive Preparation)"
        else:
            user_level = "C1/C2 (Advanced & Mastery)"
            rec_course = "كورس الإتقان الأكاديمي والتحضير لاختبار INELT الوطني الموحد"

        # حفظ في Notion
        first_name = tg_user.first_name if tg_user else "طالب"
        username = tg_user.username if tg_user else None
        try:
            save_to_notion(first_name, username, final_score, user_level)
        except Exception as e:
            print(f"[Notion Placement Error] {e}")

        result_keyboard = [
            [InlineKeyboardButton(text="🎓 تحميل شهادتي الرسمية المعتمدة (PDF)", callback_data=f"download_cert_{final_score}_{total_q}")],
            [InlineKeyboardButton(text="📚 تصفح الكورس الموصى به لمستواك", callback_data="back_to_courses")],
            [InlineKeyboardButton(text="🔄 إعادة الاختبار بنموذج جديد", callback_data="start_placement_test")],
            [InlineKeyboardButton(text="🏠 العودة للرئيسية | Main Menu", callback_data="back_to_main_menu")]
        ]

        raw_name = (tg_user.full_name or tg_user.username or "Student") if tg_user else "Student"
        result_card = (
            f"🏆 <b>نتيجة اختبار تحديد المستوى المعتمد</b> 🎓\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>الطالب:</b> {html.escape(raw_name)}\n"
            f"📊 <b>النتيجة:</b> {final_score} من أصل {total_q} أسئلة تشخيصية.\n"
            f"🏅 <b>مستواك وفق المعيار الأوروبي (CEFR):</b>\n"
            f"👉 <b>{user_level}</b>\n\n"
            f"🎯 <b>المسار التعليمي الموصى به:</b>\n"
            f"• {rec_course}\n\n"
            f"🏛️ <b>تم توثيق نتيجتك رسمياً في قاعدة بيانات أكاديمية Fluence على Notion.</b>\n"
            f"📜 <i>تم إصدار شهادة إلكترونية رسمية معتمدة بمستواك تجدها مرفقة أدناه:</i>"
        )

        try:
            await callback.message.edit_text(result_card, reply_markup=InlineKeyboardMarkup(inline_keyboard=result_keyboard), parse_mode="HTML")
        except Exception:
            await callback.message.answer(result_card, reply_markup=InlineKeyboardMarkup(inline_keyboard=result_keyboard), parse_mode="HTML")
        await callback.answer()

        # توليد وإرسال الشهادة الرسمية تلقائياً
        if tg_user:
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
                        f"🎓 <b>شهادة إلكترونية رسمية معتمدة | Official Certificate</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"تمنح أكاديمية Fluence هذه الشهادة للطالب <b>{html.escape(raw_name)}</b> "
                        f"لاجتيازه اختبار قياس المستوى بنتيجة <b>{final_score}/{total_q}</b> ومستوى <b>{user_level}</b>.\n\n"
                        f"المشرف العام: <b>Lect. Mohammed Hussein</b>\n"
                        f"رقم التوثيق: <code>{cert_id}</code>"
                    )
                    try:
                        await callback.message.answer_document(
                            document=doc,
                            caption=caption,
                            parse_mode="HTML"
                        )
                    except Exception:
                        if callback.bot and tg_user:
                            await callback.bot.send_document(
                                chat_id=tg_user.id,
                                document=doc,
                                caption=caption,
                                parse_mode="HTML"
                            )
            except Exception as cert_err:
                print(f"[Auto Certificate Delivery Error] {cert_err}")

        # تنظيف الجلسة
        placement_sessions.pop(user_id, None)

@quizzes_router.callback_query(F.data.startswith("download_cert_"))
async def handle_download_cert_callback(callback: CallbackQuery):
    """Generates and delivers the official PDF Certificate of English Proficiency on demand."""
    try:
        await callback.answer("🎓 جاري إعداد وتصدير شهادتك الرسمية المعتمدة...")
    except Exception:
        pass

    parts = callback.data.split("_")
    score = int(parts[2]) if len(parts) > 2 else 10
    total_q = int(parts[3]) if len(parts) > 3 else 20

    if score <= 4:
        level_name = "A1 (Beginner)"
    elif score <= 8:
        level_name = "A2 (Elementary)"
    elif score <= 12:
        level_name = "B1 (Intermediate)"
    elif score <= 16:
        level_name = "B2 (Upper-Intermediate)"
    else:
        level_name = "C1/C2 (Advanced & Mastery)"

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
                await callback.message.answer_document(
                    document=doc,
                    caption=caption,
                    parse_mode="HTML"
                )
            except Exception:
                if callback.bot and tg_user:
                    await callback.bot.send_document(
                        chat_id=tg_user.id,
                        document=doc,
                        caption=caption,
                        parse_mode="HTML"
                    )
        else:
            await callback.answer("⚠️ تعذر إنشاء الشهادة حالياً، يرجى المحاولة بعد قليل.", show_alert=True)
    except Exception as e:
        print(f"[Certificate Download Error] {e}")
        await callback.message.answer("⚠️ حدث تأخر مؤقت في إصدار ملف الشهادة. يرجى المحاولة مرة أخرى.")
