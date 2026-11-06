import asyncio
import os
import requests
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from datetime import datetime, timezone

from app.database.connection import AsyncSessionLocal
from app.database.models import User, Quiz, QuizQuestion, QuizAnswer, QuizAttempt, StudentProgress
from app.core.config import settings

def save_to_notion(first_name, username, score, level):
    url = "https://api.notion.com/v1/pages"
    
    # تفاصيل الربط الخاصة بـ Fluence Academy
    token = os.getenv("NOTION_API_TOKEN") or getattr(settings, "NOTION_API_TOKEN", None) or "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"
    database_id = os.getenv("NOTION_DATABASE_ID") or getattr(settings, "NOTION_DATABASE_ID", None) or "7ae3e7572bf54b198a13816b43c90e05"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # معالجة حالة عدم وجود معرف (Username) للطالب
    username_text = f"@{username}" if username else "لا يوجد معرف"

    # هيكل البيانات المطابق لأعمدة الجدول
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
        if response.status_code not in [200, 201]:
            print(f"Notion Error: {response.text}")
        else:
            print(f"Notion Success: Saved placement result for {first_name} (Score: {score}/20, Level: {level})")
    except Exception as e:
        print(f"Failed to connect to Notion: {e}")

quizzes_router = Router(name="quizzes_router")

@quizzes_router.callback_query(F.data.startswith("start_quiz_"))
async def handle_start_quiz(callback: CallbackQuery):
    """Starts the quiz for a given lesson."""
    lesson_id = int(callback.data.split("_")[-1])

    async with AsyncSessionLocal() as session:
        q_query = select(Quiz).where(Quiz.lesson_id == lesson_id)
        q_result = await session.execute(q_query)
        quiz = q_result.scalar_one_or_none()

        if not quiz:
            await callback.answer("No quiz available for this lesson yet.", show_alert=True)
            return

        # Fetch first question
        quest_query = select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.order_index)
        quest_result = await session.execute(quest_query)
        questions = quest_result.scalars().all()

        if not questions:
            await callback.answer("Quiz questions are being prepared.", show_alert=True)
            return

        total_questions = len(questions)
        first_q = questions[0]

        # Fetch answers for Q1
        ans_query = select(QuizAnswer).where(QuizAnswer.question_id == first_q.id)
        ans_result = await session.execute(ans_query)
        answers = ans_result.scalars().all()

    # Build question text and buttons
    text = (
        f"📝 <b>{quiz.title}</b>\n\n"
        f"<b>Question 1 of {total_questions}:</b>\n\n"
        f"❓ {first_q.question_text}"
    )

    keyboard = []
    for ans in answers:
        # callback: ans_{quiz_id}_{q_index}_{ans_id}_{current_score}
        keyboard.append([
            InlineKeyboardButton(
                text=ans.answer_text,
                callback_data=f"ans_{quiz.id}_0_{ans.id}_0"
            )
        ])

    await callback.message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()

@quizzes_router.callback_query(F.data.startswith("ans_"))
async def handle_answer_selected(callback: CallbackQuery):
    """Processes student answer and advances to next question or final score."""
    parts = callback.data.split("_")
    quiz_id = int(parts[1])
    q_index = int(parts[2])
    selected_ans_id = int(parts[3])
    current_score = int(parts[4])

    async with AsyncSessionLocal() as session:
        # Check selected answer
        ans_query = select(QuizAnswer).where(QuizAnswer.id == selected_ans_id)
        ans_result = await session.execute(ans_query)
        selected_ans = ans_result.scalar_one_or_none()

        # Fetch all questions for this quiz
        quest_query = select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.order_index)
        quest_result = await session.execute(quest_query)
        questions = quest_result.scalars().all()

        # Fetch quiz
        quiz_query = select(Quiz).where(Quiz.id == quiz_id)
        quiz_result = await session.execute(quiz_query)
        quiz = quiz_result.scalar_one_or_none()

    if not selected_ans or not quiz:
        await callback.answer("Error processing answer.", show_alert=True)
        return

    is_correct = selected_ans.is_correct
    current_q = questions[q_index]
    explanation = current_q.explanation or ""

    if is_correct:
        current_score += current_q.points
        feedback = "✅ <b>Correct!</b>"
    else:
        feedback = "❌ <b>Incorrect.</b>"

    if explanation:
        feedback += f"\n<i>💡 {explanation}</i>"

    next_q_index = q_index + 1
    total_questions = len(questions)

    if next_q_index < total_questions:
        # Load next question
        next_q = questions[next_q_index]

        async with AsyncSessionLocal() as session:
            next_ans_query = select(QuizAnswer).where(QuizAnswer.question_id == next_q.id)
            next_ans_result = await session.execute(next_ans_query)
            next_answers = next_ans_result.scalars().all()

        text = (
            f"{feedback}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>Question {next_q_index + 1} of {total_questions}:</b>\n\n"
            f"❓ {next_q.question_text}"
        )

        keyboard = []
        for ans in next_answers:
            keyboard.append([
                InlineKeyboardButton(
                    text=ans.answer_text,
                    callback_data=f"ans_{quiz.id}_{next_q_index}_{ans.id}_{current_score}"
                )
            ])

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
    else:
        # Quiz completed! Calculate final score
        max_score = sum(q.points for q in questions)
        percentage = round((current_score / max_score) * 100, 1) if max_score > 0 else 0
        passed = percentage >= quiz.pass_percentage

        # Save attempt in database
        tg_user = callback.from_user
        async with AsyncSessionLocal() as session:
            user_query = select(User).where(User.telegram_id == tg_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()

            if user:
                attempt = QuizAttempt(
                    student_id=user.id,
                    quiz_id=quiz.id,
                    score_percentage=percentage,
                    passed=passed,
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc)
                )
                session.add(attempt)

                # If passed and linked to lesson, record lesson completion
                if passed and quiz.lesson_id:
                    prog_check = select(StudentProgress).where(
                        StudentProgress.student_id == user.id,
                        StudentProgress.lesson_id == quiz.lesson_id
                    )
                    prog_res = await session.execute(prog_check)
                    existing_prog = prog_res.scalar_one_or_none()

                    if not existing_prog:
                        prog = StudentProgress(
                            student_id=user.id,
                            lesson_id=quiz.lesson_id,
                            is_completed=True
                        )
                        session.add(prog)

                await session.commit()

        if passed:
            result_header = "🎉 <b>CONGRATULATIONS! YOU PASSED!</b> 🌟"
            status_text = "Status: <b>PASSED ✅</b>"
        else:
            result_header = "📚 <b>KEEP PRACTICING!</b>"
            status_text = f"Status: <b>NOT PASSED ❌</b> (Passing grade: {quiz.pass_percentage}%)"

        final_text = (
            f"{feedback}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{result_header}\n\n"
            f"<b>Quiz:</b> {quiz.title}\n"
            f"<b>Your Score:</b> {percentage}%\n"
            f"{status_text}\n\n"
            f"<i>Your score has been permanently saved to your academy records!</i>"
        )

        keyboard = [
            [InlineKeyboardButton(text="📚 Browse More Courses", callback_data="back_to_catalog")]
        ]

        await callback.message.edit_text(
            final_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )

    await callback.answer()

# ---------------------------------------------------------------------------
# 20-Question Diagnostic Placement Test Definition
# ---------------------------------------------------------------------------
PLACEMENT_QUESTIONS = [
    {
        "question": "I ___ from Iraq.",
        "options": ["am", "is", "are", "be"],
        "correct": 0
    },
    {
        "question": "She ___ to the university every day.",
        "options": ["go", "goes", "going", "went"],
        "correct": 1
    },
    {
        "question": "We ___ a great play at the theater last night.",
        "options": ["saw", "seen", "seeing", "see"],
        "correct": 0
    },
    {
        "question": "If it rains tomorrow, we ___ the lecture.",
        "options": ["cancel", "will cancel", "cancelled", "would cancel"],
        "correct": 1
    },
    {
        "question": "The research ___ published in 2022.",
        "options": ["was", "is", "has", "had"],
        "correct": 0
    },
    {
        "question": "If I had known about the seminar, I ___.",
        "options": ["would attend", "attended", "would have attended", "will attend"],
        "correct": 2
    },
    {
        "question": "Which word has a silent 'b'?",
        "options": ["problem", "debt", "rabbit", "combine"],
        "correct": 1
    },
    {
        "question": "Which word has a different vowel sound?",
        "options": ["meat", "seat", "great", "heat"],
        "correct": 2
    },
    {
        "question": "Which word rhymes with \"tough\"?",
        "options": ["though", "rough", "through", "dough"],
        "correct": 1
    },
    {
        "question": "In \"PHOTOGRAPHER\", which syllable has the main stress?",
        "options": ["1st", "2nd", "3rd", "4th"],
        "correct": 1
    },
    {
        "question": "Which word contains a silent 'k'?",
        "options": ["ask", "make", "know", "like"],
        "correct": 2
    },
    {
        "question": "Which word has the same vowel sound as \"hair\"?",
        "options": ["hear", "bear", "beer", "fear"],
        "correct": 1
    },
    {
        "question": "\"Would you mind opening the window?\" - \"___\"",
        "options": ["Yes, I mind", "No, not at all", "Yes, please", "No, I don't"],
        "correct": 1
    },
    {
        "question": "The student needs to ___ up his mind.",
        "options": ["make", "take", "do", "get"],
        "correct": 0
    },
    {
        "question": "I've been studying literature ___ 5 years.",
        "options": ["since", "for", "ago", "from"],
        "correct": 1
    },
    {
        "question": "The new policy is on the ___ of collapse.",
        "options": ["edge", "brink", "border", "boundary"],
        "correct": 1
    },
    {
        "question": "Seldom ___ such a brilliantly written essay.",
        "options": ["I have read", "have I read", "I read", "did I read"],
        "correct": 1
    },
    {
        "question": "You ___ have left your keys in the hall; it was locked.",
        "options": ["mustn't", "shouldn't", "couldn't", "wouldn't"],
        "correct": 2
    },
    {
        "question": "I can't ___ what the author is trying to say.",
        "options": ["make out", "make up", "make off", "make for"],
        "correct": 0
    },
    {
        "question": "His presentation was completely ___.",
        "options": ["lucid", "opaque", "transparent", "candid"],
        "correct": 1
    }
]

def get_placement_level_info(score: int) -> tuple[str, str]:
    """
    Returns (level_name, target_callback) based on score out of 20:
    0-4: 🌱 Beginner (A1) -> level_a1
    5-8: 📘 Elementary (A2) -> level_a2
    9-12: 📙 Pre-Intermediate (B1) -> level_b1
    13-15: 📕 Intermediate & Upper (B2) -> level_b2
    16-18: 🎓 Advanced (C1) -> level_c1
    19-20: 🏆 Proficiency (C2) -> level_c2
    """
    if score <= 4:
        return "🌱 Beginner (A1)", "level_a1"
    elif score <= 8:
        return "📘 Elementary (A2)", "level_a2"
    elif score <= 12:
        return "📙 Pre-Intermediate (B1)", "level_b1"
    elif score <= 15:
        return "📕 Intermediate & Upper (B2)", "level_b2"
    elif score <= 18:
        return "🎓 Advanced (C1)", "level_c1"
    else:
        return "🏆 Proficiency (C2)", "level_c2"

def build_placement_question_keyboard(q_idx: int, score: int) -> InlineKeyboardMarkup:
    """Builds clean inline buttons for the given question index and running score."""
    q = PLACEMENT_QUESTIONS[q_idx]
    options = q["options"]
    keyboard = []

    # If any option is long (>14 chars), use 1 option per row, otherwise 2 per row
    max_len = max(len(opt) for opt in options)
    if max_len > 14:
        for i, opt in enumerate(options):
            keyboard.append([InlineKeyboardButton(text=opt, callback_data=f"pt_{q_idx}_{i}_{score}")])
    else:
        row = []
        for i, opt in enumerate(options):
            row.append(InlineKeyboardButton(text=opt, callback_data=f"pt_{q_idx}_{i}_{score}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="❌ إلغاء الاختبار | Cancel", callback_data="back_to_courses")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@quizzes_router.message(F.text.contains("اختبار المستوى") | F.text.contains("Placement Test"))
async def handle_placement_test(message: Message):
    """Displays the updated 20-question Placement Test overview and launch button."""
    text = (
        "📝 <b>اختبار تحديد المستوى المتقدم</b>\n\n"
        "يتكون الاختبار من <b>20 سؤالاً</b> متدرج الصعوبة تقيس مستواك في القواعد، المفردات، والتلفظ (Phonetics).\n"
        "• يرجى اختيار الإجابة الأصح لكل سؤال.\n"
        "• يعتمد تحديد مستواك بدقة على إجاباتك الفردية دون استخدام وسائل مساعدة."
    )
    keyboard = [
        [InlineKeyboardButton(text="🚀 ابدأ الاختبار الآن | Start Test", callback_data="start_placement_test")],
        [InlineKeyboardButton(text="📚 تصفح الدورات | Browse Courses", callback_data="back_to_courses")]
    ]
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@quizzes_router.callback_query(F.data == "start_placement_test")
async def handle_start_placement_test(callback: CallbackQuery):
    """Launches Question 1 of the 20-question placement test using edit_message_text."""
    first_q = PLACEMENT_QUESTIONS[0]
    text = (
        f"📝 <b>اختبار تحديد المستوى (السؤال 1 من {len(PLACEMENT_QUESTIONS)})</b>\n\n"
        f"❓ <b>{first_q['question']}</b>"
    )
    keyboard = build_placement_question_keyboard(0, 0)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@quizzes_router.callback_query(F.data.startswith("pt_"))
async def handle_placement_test_answer(callback: CallbackQuery):
    """Evaluates question answer, advances through 20 questions via edit_message_text, and gives final diagnostic evaluation."""
    parts = callback.data.split("_")
    q_idx = int(parts[1])
    selected_opt = int(parts[2])
    score = int(parts[3])

    # Check correctness
    if selected_opt == PLACEMENT_QUESTIONS[q_idx]["correct"]:
        score += 1

    next_idx = q_idx + 1

    if next_idx < len(PLACEMENT_QUESTIONS):
        next_q = PLACEMENT_QUESTIONS[next_idx]
        text = (
            f"📝 <b>اختبار تحديد المستوى (السؤال {next_idx + 1} من {len(PLACEMENT_QUESTIONS)})</b>\n\n"
            f"❓ <b>{next_q['question']}</b>"
        )
        keyboard = build_placement_question_keyboard(next_idx, score)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        # Placement test completed!
        level_name, target_callback = get_placement_level_info(score)
        final_score = score
        user_level = level_name
        message = callback.message
        result_text = (
            "📊 <b>نتيجة اختبار تحديد المستوى | Placement Test Result</b>\n\n"
            f"لقد أجبت بشكل صحيح على <b>{score}</b> من أصل {len(PLACEMENT_QUESTIONS)} سؤالاً.\n"
            f"مستواك اللغوي الحالي هو: <b>{level_name}</b>\n\n"
            "🎯 الكورس التدريبي الموصى به لك هو كورس اللغة العامة لهذا المستوى، حيث سيعمل على تطوير نقاط قوتك ومعالجة نقاط ضعفك في القواعد، المفردات، والتلفظ."
        )
        result_keyboard = [
            [InlineKeyboardButton(text="📖 عرض تفاصيل كورس مستواي", callback_data=target_callback)],
            [InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية | Main Menu", callback_data="back_to_main_menu")]
        ]

        # Record attempt asynchronously in academy database
        tg_user = callback.from_user
        if tg_user:
            try:
                async with AsyncSessionLocal() as session:
                    u_query = select(User).where(User.telegram_id == tg_user.id)
                    u_res = await session.execute(u_query)
                    user = u_res.scalar_one_or_none()
                    if user:
                        # Find or create Quiz record for placement
                        q_find = select(Quiz).where(Quiz.title.ilike("%Placement%"))
                        q_res = await session.execute(q_find)
                        placement_quiz = q_res.scalar_one_or_none()
                        if not placement_quiz:
                            placement_quiz = Quiz(
                                title="Comprehensive Placement Test (20 Questions)",
                                pass_percentage=50,
                                is_active=True
                            )
                            session.add(placement_quiz)
                            await session.flush()

                        attempt = QuizAttempt(
                            student_id=user.id,
                            quiz_id=placement_quiz.id,
                            score_percentage=round((score / len(PLACEMENT_QUESTIONS)) * 100, 1),
                            passed=score >= 10,
                            started_at=datetime.now(timezone.utc),
                            completed_at=datetime.now(timezone.utc)
                        )
                        session.add(attempt)
                        await session.commit()
            except Exception as e:
                print(f"[Placement Attempt Save Error] {e}")

        await callback.message.edit_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=result_keyboard),
            parse_mode="HTML"
        )

        # استدعاء دالة حفظ النتيجة في Notion
        try:
            first_name = (message.chat.first_name if (message and message.chat) else None) or (tg_user.first_name if tg_user else "طالب مجهول")
            username = (message.chat.username if (message and message.chat) else None) or (tg_user.username if tg_user else None)

            # تنفيذ غير حاجب (Non-blocking async thread) لضمان عدم بطء أو توقف البوت
            asyncio.create_task(
                asyncio.to_thread(
                    save_to_notion,
                    first_name,
                    username,
                    final_score,
                    user_level
                )
            )
        except Exception as e:
            print(f"[Notion Integration Error] Failed to schedule Notion push: {e}")

    await callback.answer()

@quizzes_router.message(F.text.contains("الاختبارات اليومية") | F.text.contains("Quizzes"))
async def handle_quizzes_and_grades(message: Message):
    """Displays student quiz history, daily challenges, and scores."""
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

        # Fetch recent attempts
        att_query = select(QuizAttempt).where(QuizAttempt.student_id == user.id).order_by(QuizAttempt.completed_at.desc())
        att_result = await session.execute(att_query)
        attempts = att_result.scalars().all()

        # Fetch available quizzes
        quizzes_q = select(Quiz).limit(5)
        quizzes_res = await session.execute(quizzes_q)
        available_quizzes = quizzes_res.scalars().all()

    text = f"🎯 <b>قسم الاختبارات والتقييم اليومي | Quizzes & Grades</b>\n\n"
    text += f"👤 <b>الطالب:</b> {user.full_name}\n"

    if attempts:
        text += f"📊 <b>نتائج آخر الاختبارات المنجزة:</b>\n"
        for att in attempts[:5]:
            badge = "✅ ناجح" if att.passed else "❌ تدرب أكثر"
            date_str = att.completed_at.strftime("%Y-%m-%d")
            text += f"• اختبار #{att.quiz_id}: النتيجة <b>{att.score_percentage}%</b> ({badge}) <i>{date_str}</i>\n"
        text += "\n"
    else:
        text += "لم تقم بأداء أي اختبارات بعد. ابدأ الآن بتحدي معلوماتك اليومية! 🚀\n\n"

    keyboard = []
    if available_quizzes:
        text += "📝 <b>اختر اختباراً للبدء الآن:</b>"
        for q in available_quizzes:
            keyboard.append([InlineKeyboardButton(text=f"✍️ {q.title}", callback_data=f"start_quiz_{q.lesson_id or q.id}")])

    keyboard.append([InlineKeyboardButton(text="📚 الانتقال للدورات | Courses", callback_data="back_to_courses")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
