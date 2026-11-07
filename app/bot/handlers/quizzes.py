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

# 1. تهيئة راوتر الاختبارات
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

# ---------------------------------------------------------------------------
# محرك إنشاء الشهادات الإلكترونية الرسمية المعتمدة (100% Pure Python)
# ---------------------------------------------------------------------------
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
    stream_ops.append('1 1 1 rg 0 0 842 595 re f')
    stream_ops.append('0.06 0.13 0.28 RG 6 w 25 25 792 545 re S')
    stream_ops.append('0.79 0.65 0.27 RG 2 w 35 35 772 525 re S')
    stream_ops.append('0.06 0.13 0.28 RG 0.8 w 41 41 760 513 re S')
    stream_ops.append('0.79 0.65 0.27 rg 33 33 12 12 re f 797 33 12 12 re f 33 550 12 12 re f 797 550 12 12 re f')

    if logo_bytes:
        stream_ops.append('q 64 0 0 64 389 488 cm /Im1 Do Q')

    stream_ops.append('BT /F2 18 Tf 0.06 0.13 0.28 rg 290 460 Td (FLUENCE ENGLISH ACADEMY) Tj ET')
    stream_ops.append('BT /F4 10 Tf 0.79 0.65 0.27 rg 305 444 Td (ACCREDITED LANGUAGE & ACADEMIC PLATFORM) Tj ET')
    stream_ops.append('BT /F3 26 Tf 0.08 0.16 0.35 rg 215 395 Td (CERTIFICATE OF PROFICIENCY) Tj ET')
    stream_ops.append('BT /F4 11 Tf 0.45 0.50 0.58 rg 270 375 Td (COMMON EUROPEAN FRAMEWORK OF REFERENCE - CEFR) Tj ET')
    stream_ops.append('BT /F1 12 Tf 0.35 0.38 0.44 rg 355 335 Td (This is to certify that) Tj ET')

    name_x = max(100, int(421 - (len(clean_name) * 11 / 2)))
    stream_ops.append(f'BT /F2 22 Tf 0.08 0.16 0.35 rg {name_x} 300 Td ({clean_name}) Tj ET')
    stream_ops.append('0.79 0.65 0.27 RG 1.5 w 250 292 m 592 292 l S')

    stream_ops.append('BT /F1 11.5 Tf 0.25 0.28 0.34 rg 170 262 Td (has successfully completed the comprehensive diagnostic English placement assessment) Tj ET')
    stream_ops.append('BT /F1 11.5 Tf 0.25 0.28 0.34 rg 210 244 Td (demonstrating proven academic competence and linguistic proficiency evaluated at:) Tj ET')

    stream_ops.append('0.06 0.13 0.28 rg 271 185 300 42 re f')
    stream_ops.append('0.79 0.65 0.27 RG 2 w 271 185 300 42 re S')
    badge_text = f'CEFR LEVEL: {clean_level}'
    badge_x = int(421 - (len(badge_text) * 8.5 / 2))
    stream_ops.append(f'BT /F2 15 Tf 1 1 1 rg {badge_x} 200 Td ({badge_text}) Tj ET')

    score_text = f'Official Assessment Score: {score}/{total_questions} - {percentage}%'
    score_x = int(421 - (len(score_text) * 6.5 / 2))
    stream_ops.append(f'BT /F2 10.5 Tf 0.08 0.16 0.35 rg {score_x} 165 Td ({score_text}) Tj ET')

    stream_ops.append('0.79 0.65 0.27 RG 1 w 70 148 m 260 148 l S')
    stream_ops.append(f'BT /F2 9.5 Tf 0.15 0.18 0.24 rg 70 133 Td (Credential ID: {clean_id}) Tj ET')
    stream_ops.append(f'BT /F1 9 Tf 0.30 0.35 0.42 rg 70 119 Td (Issue Date: {clean_date}) Tj ET')
    stream_ops.append('BT /F4 8 Tf 0.45 0.50 0.58 rg 70 105 Td (Verified in Fluence Academy Notion Registry) Tj ET')

    if logo_bytes:
        stream_ops.append('q 60 0 0 60 391 80 cm /Im1 Do Q')

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

# ---------------------------------------------------------------------------
# دالة الحفظ التلقائي في Notion
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# بنك أسئلة اختبار تحديد المستوى المتجدد (CEFR Placement Pool)
# ---------------------------------------------------------------------------
PLACEMENT_QUESTION_BANK = {
    "A1": [
        {"question": "What ___ your name?", "correct_ans": "is", "distractors": ["are", "am", "be"]},
        {"question": "Where ___ you from?", "correct_ans": "are", "distractors": ["is", "am", "be"]},
        {"question": "She ___ two brothers and one sister.", "correct_ans": "has", "distractors": ["have", "having", "is"]},
        {"question": "I usually get up ___ 7 o'clock.", "correct_ans": "at", "distractors": ["on", "in", "to"]},
        {"question": "They ___ students at the university.", "correct_ans": "are", "distractors": ["is", "am", "be"]},
        {"question": "Which word is a fruit?", "correct_ans": "Apple", "distractors": ["Table", "Window", "Pencil"]},
    ],
    "A2": [
        {"question": "Yesterday, we ___ to the central library.", "correct_ans": "went", "distractors": ["go", "gone", "going"]},
        {"question": "Look! The children ___ football in the garden.", "correct_ans": "are playing", "distractors": ["play", "played", "is playing"]},
        {"question": "This dictionary is ___ than that one.", "correct_ans": "more useful", "distractors": ["usefuler", "most useful", "as useful"]},
        {"question": "Have you ever ___ to London?", "correct_ans": "been", "distractors": ["be", "was", "went"]},
        {"question": "I don't have ___ money in my wallet.", "correct_ans": "any", "distractors": ["some", "no", "many"]},
        {"question": "Which of these is the opposite of \"generous\"?", "correct_ans": "Stingy", "distractors": ["Polite", "Brave", "Kind"]},
    ],
    "B1": [
        {"question": "If it ___ tomorrow, we will postpone the lecture.", "correct_ans": "rains", "distractors": ["will rain", "rained", "rain"]},
        {"question": "The monograph ___ by the professor last semester.", "correct_ans": "was written", "distractors": ["wrote", "is written", "has written"]},
        {"question": "I have lived in this city ___ ten years.", "correct_ans": "for", "distractors": ["since", "from", "during"]},
        {"question": "You ___ park your vehicle here; it is strictly prohibited.", "correct_ans": "mustn't", "distractors": ["don't have to", "needn't", "might not"]},
        {"question": "She asked me where ___ .", "correct_ans": "I lived", "distractors": ["did I live", "do I live", "I live"]},
        {"question": "He gave up ___ after the doctor warned him.", "correct_ans": "smoking", "distractors": ["to smoke", "smoke", "smoked"]},
    ],
    "B2": [
        {"question": "If I had known about the conference, I ___.", "correct_ans": "would have attended", "distractors": ["would attend", "attended", "will attend"]},
        {"question": "You ___ have left your keys in the hall; it was locked all day.", "correct_ans": "couldn't", "distractors": ["mustn't", "shouldn't", "wouldn't"]},
        {"question": "The economy was on the ___ of collapse.", "correct_ans": "brink", "distractors": ["edge", "border", "boundary"]},
        {"question": "She succeeded ___ passing the challenging examination.", "correct_ans": "in", "distractors": ["on", "at", "with"]},
        {"question": "Despite ___ hard, the team did not qualify.", "correct_ans": "working", "distractors": ["worked", "work", "to work"]},
        {"question": "He was accused ___ leaking confidential research materials.", "correct_ans": "of", "distractors": ["for", "with", "about"]},
    ],
    "C1": [
        {"question": "Seldom ___ such an insightful analysis of literature.", "correct_ans": "have I read", "distractors": ["I have read", "I read", "did I read"]},
        {"question": "His explanation was completely ___, leaving everyone confused.", "correct_ans": "opaque", "distractors": ["lucid", "transparent", "candid"]},
        {"question": "Scarcely had she finished speaking ___ the audience applauded.", "correct_ans": "when", "distractors": ["than", "then", "as"]},
        {"question": "The dean recommended that the curriculum ___ updated immediately.", "correct_ans": "be", "distractors": ["is", "was", "would be"]},
        {"question": "Under no circumstances ___ the examination hall before time.", "correct_ans": "should you leave", "distractors": ["you should leave", "you leave", "you will leave"]},
        {"question": "His arguments were so ___ that no one refuted them.", "correct_ans": "compelling", "distractors": ["tenuous", "fallacious", "equivocal"]},
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
# مشغل اختبار تحديد المستوى (من القائمة السفلية ومن رسالة /start)
# ---------------------------------------------------------------------------
@quizzes_router.message(F.text.contains("اختبار المستوى") | F.text.contains("Placement Test") | F.text.contains("تحديد المستوى"))
async def handle_placement_test(message: Message):
    """Displays the updated 20-question Placement Test overview and launch button."""
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
    """Generates a fresh, randomized 20-question placement test and launches Question 1."""
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
    """Evaluates question answer, advances through 20 questions, and issues the official certificate."""
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
