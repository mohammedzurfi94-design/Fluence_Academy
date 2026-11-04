from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from datetime import datetime, timezone

from app.database.connection import AsyncSessionLocal
from app.database.models import User, Quiz, QuizQuestion, QuizAnswer, QuizAttempt, StudentProgress

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

@quizzes_router.message(F.text.in_(["📝 اختبار المستوى | Placement Test"]))
async def handle_placement_test(message: Message):
    """Displays the academic Placement Test overview and launch button."""
    async with AsyncSessionLocal() as session:
        # Check if there is an existing quiz
        q_query = select(Quiz).limit(1)
        q_result = await session.execute(q_query)
        quiz = q_result.scalar_one_or_none()

    quiz_callback = f"start_quiz_{quiz.lesson_id or quiz.id}" if quiz else "browse_available_lessons"

    text = (
        "📝 <b>اختبار تحديد المستوى الأكاديمي | English Placement Test</b>\n\n"
        "صُمم هذا الاختبار المعتمد لتحديد مستواك الحقيقي في اللغة الإنجليزية "
        "بدقة وفق المعيار الأوروبي المشترك (A1 - C1).\n\n"
        "📌 <b>تفاصيل الاختبار:</b>\n"
        "• يغطي المهارات الأساسية: القواعد (Grammar)، المفردات (Vocabulary)، وتراكيب الجمل.\n"
        "• أسئلة متدرجة الصعوبة باختيارات متعددة.\n"
        "• تقييم فوري وتحديد دقيق للمستوى والمسار التدريبي الأنسب لك.\n\n"
        "جاهز للبدء؟ اضغط على الزر أدناه وانطلق: 👇"
    )
    keyboard = [
        [InlineKeyboardButton(text="🚀 بدء اختبار تحديد المستوى | Start Test", callback_data=quiz_callback)],
        [InlineKeyboardButton(text="📚 تصفح الدورات | Browse Courses", callback_data="back_to_courses")]
    ]
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@quizzes_router.message(F.text.in_(["🎯 الاختبارات اليومية | Quizzes", "📝 Quizzes & Grades"]))
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
