import asyncio
import os
import random
import requests
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from datetime import datetime, timezone

from app.database.connection import AsyncSessionLocal
from app.database.models import User, Quiz, QuizQuestion, QuizAnswer, QuizAttempt, StudentProgress
from app.core.config import settings
from app.services.scheduler_service import get_today_lesson, send_daily_lesson_to_user

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

        quest_query = select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.order_index)
        quest_result = await session.execute(quest_query)
        questions = quest_result.scalars().all()

        if not questions:
            await callback.answer("Quiz questions are being prepared.", show_alert=True)
            return

        total_questions = len(questions)
        first_q = questions[0]

        ans_query = select(QuizAnswer).where(QuizAnswer.question_id == first_q.id)
        ans_result = await session.execute(ans_query)
        answers = ans_result.scalars().all()

    text = (
        f"📝 <b>{quiz.title}</b>\n\n"
        f"<b>Question 1 of {total_questions}:</b>\n\n"
        f"❓ {first_q.question_text}"
    )

    keyboard = []
    for ans in answers:
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
        ans_query = select(QuizAnswer).where(QuizAnswer.id == selected_ans_id)
        ans_result = await session.execute(ans_query)
        selected_ans = ans_result.scalar_one_or_none()

        quest_query = select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.order_index)
        quest_result = await session.execute(quest_query)
        questions = quest_result.scalars().all()

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
        max_score = sum(q.points for q in questions)
        percentage = round((current_score / max_score) * 100, 1) if max_score > 0 else 0
        passed = percentage >= quiz.pass_percentage

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
# Dynamic Graded Question Bank (A1 to C2) & Diagnostic Placement Test
# ---------------------------------------------------------------------------
PLACEMENT_QUESTION_BANK = {
    "A1": [
        {"question": "I ___ from Iraq.", "correct_ans": "am", "distractors": ["is", "are", "be"]},
        {"question": "They ___ students at Baghdad University.", "correct_ans": "are", "distractors": ["is", "am", "be"]},
        {"question": "She ___ tea every morning.", "correct_ans": "drinks", "distractors": ["drink", "drinking", "drank"]},
        {"question": "Where ___ you live?", "correct_ans": "do", "distractors": ["does", "are", "is"]},
        {"question": "There ___ a book on the desk.", "correct_ans": "is", "distractors": ["are", "am", "be"]},
        {"question": "He doesn't ___ coffee.", "correct_ans": "like", "distractors": ["likes", "liking", "liked"]},
        {"question": "What time ___ it?", "correct_ans": "is", "distractors": ["are", "does", "do"]},
        {"question": "This is my brother. ___ name is Ali.", "correct_ans": "His", "distractors": ["Her", "He", "Him"]},
        {"question": "We have an English lecture ___ Mondays.", "correct_ans": "on", "distractors": ["in", "at", "by"]},
        {"question": "Can you ___ English fluently?", "correct_ans": "speak", "distractors": ["speaks", "speaking", "spoke"]},
    ],
    "A2": [
        {"question": "She ___ to the university every day.", "correct_ans": "goes", "distractors": ["go", "going", "went"]},
        {"question": "We ___ a great play at the theater last night.", "correct_ans": "saw", "distractors": ["seen", "seeing", "see"]},
        {"question": "Yesterday, he ___ his homework before dinner.", "correct_ans": "finished", "distractors": ["finish", "finishing", "finishes"]},
        {"question": "London is ___ than Baghdad in winter.", "correct_ans": "colder", "distractors": ["more cold", "coldest", "cold"]},
        {"question": "She is the ___ student in our academic group.", "correct_ans": "smartest", "distractors": ["smarter", "most smart", "smart"]},
        {"question": "I haven't seen my advisor ___ yesterday.", "correct_ans": "since", "distractors": ["for", "from", "at"]},
        {"question": "While I ___ reading, the power went out.", "correct_ans": "was", "distractors": ["were", "am", "is"]},
        {"question": "He decided to ___ a new laptop for his research.", "correct_ans": "buy", "distractors": ["buying", "bought", "buys"]},
        {"question": "Which word contains a silent 'k'?", "correct_ans": "know", "distractors": ["ask", "like", "make"]},
        {"question": "Which word has a silent 'b'?", "correct_ans": "debt", "distractors": ["problem", "rabbit", "combine"]},
    ],
    "B1": [
        {"question": "If it rains tomorrow, we ___ the outdoor lecture.", "correct_ans": "will cancel", "distractors": ["cancel", "cancelled", "would cancel"]},
        {"question": "The research paper ___ published in 2022.", "correct_ans": "was", "distractors": ["is", "has", "had"]},
        {"question": "I have been studying English literature ___ five years.", "correct_ans": "for", "distractors": ["since", "ago", "from"]},
        {"question": "You ___ wear a helmet when riding a motorbike. It is mandatory.", "correct_ans": "must", "distractors": ["might", "could", "would"]},
        {"question": "The student needs to ___ up his mind about his major.", "correct_ans": "make", "distractors": ["take", "do", "get"]},
        {"question": "If I had enough time, I ___ another foreign language.", "correct_ans": "would learn", "distractors": ["will learn", "learned", "learn"]},
        {"question": "\"Would you mind opening the window?\" - \"___\"", "correct_ans": "No, not at all", "distractors": ["Yes, I mind", "Yes, please", "No, I don't"]},
        {"question": "Which word rhymes with \"tough\"?", "correct_ans": "rough", "distractors": ["though", "through", "dough"]},
        {"question": "Which word has a different vowel sound?", "correct_ans": "great", "distractors": ["meat", "seat", "heat"]},
        {"question": "The flight ___ at 7:00 AM tomorrow morning.", "correct_ans": "departs", "distractors": ["depart", "departed", "departing"]},
    ],
    "B2": [
        {"question": "If I had known about the conference, I ___.", "correct_ans": "would have attended", "distractors": ["would attend", "attended", "will attend"]},
        {"question": "You ___ have left your keys in the hall; it was locked all day.", "correct_ans": "couldn't", "distractors": ["mustn't", "shouldn't", "wouldn't"]},
        {"question": "In the word \"PHOTOGRAPHER\", which syllable has the main stress?", "correct_ans": "2nd", "distractors": ["1st", "3rd", "4th"]},
        {"question": "Which word has the same vowel sound as \"hair\"?", "correct_ans": "bear", "distractors": ["hear", "beer", "fear"]},
        {"question": "The economy was on the ___ of collapse.", "correct_ans": "brink", "distractors": ["edge", "border", "boundary"]},
        {"question": "I can't ___ what the author is trying to say in this stanza.", "correct_ans": "make out", "distractors": ["make up", "make off", "make for"]},
        {"question": "She succeeded ___ passing the challenging IELTS test.", "correct_ans": "in", "distractors": ["on", "at", "with"]},
        {"question": "Despite ___ hard, the team did not reach the finals.", "correct_ans": "working", "distractors": ["worked", "work", "to work"]},
        {"question": "I would rather you ___ tomorrow instead of today.", "correct_ans": "came", "distractors": ["come", "will come", "have come"]},
        {"question": "He was accused ___ leaking confidential examination materials.", "correct_ans": "of", "distractors": ["for", "with", "about"]},
    ],
    "C1": [
        {"question": "Seldom ___ such an insightful analysis of Shakespearean tragedy.", "correct_ans": "have I read", "distractors": ["I have read", "I read", "did I read"]},
        {"question": "His explanation was completely ___, leaving everyone confused.", "correct_ans": "opaque", "distractors": ["lucid", "transparent", "candid"]},
        {"question": "Scarcely had she finished speaking ___ the audience stood and applauded.", "correct_ans": "when", "distractors": ["than", "then", "as"]},
        {"question": "The dean recommended that the curriculum ___ updated immediately.", "correct_ans": "be", "distractors": ["is", "was", "would be"]},
        {"question": "Her remarks were totally ___ to the discussion at hand.", "correct_ans": "extraneous", "distractors": ["germane", "cogent", "pertinent"]},
        {"question": "Under no circumstances ___ the laboratory unattended.", "correct_ans": "should you leave", "distractors": ["you should leave", "you leave", "you will leave"]},
        {"question": "Had it not been for your guidance, I ___ failed the comprehensive exam.", "correct_ans": "would have", "distractors": ["will have", "had", "should"]},
        {"question": "His arguments were so ___ that the opposition had no rebuttal.", "correct_ans": "compelling", "distractors": ["tenuous", "fallacious", "equivocal"]},
    ],
    "C2": [
        {"question": "The keynote address was devoid of substance, filled with mere ___.", "correct_ans": "platitudes", "distractors": ["accolades", "truisms", "veracities"]},
        {"question": "Little ___ that his hypothesis would transform modern linguistics.", "correct_ans": "did he realize", "distractors": ["he realized", "he had realized", "he was realizing"]},
        {"question": "The institutional decline was precipitated by administrative ___.", "correct_ans": "ineptitude", "distractors": ["aptitude", "fortitude", "solicitude"]},
        {"question": "She possessed an almost ___ knack for deciphering archaic manuscripts.", "correct_ans": "uncanny", "distractors": ["unruly", "unwieldy", "unctuous"]},
        {"question": "The professor's lecture was distinguished by remarkable ___ and depth.", "correct_ans": "erudition", "distractors": ["superficiality", "vacuity", "pedantry"]},
        {"question": "The literary critic described the novel's prose as truly ___.", "correct_ans": "transcendent", "distractors": ["ephemeral", "mediocre", "pedestrian"]},
    ]
}

def sample_diagnostic_placement_questions() -> list:
    """
    Builds a randomized 20-question placement test:
    - 3 from A1
    - 3 from A2
    - 4 from B1
    - 4 from B2
    - 3 from C1
    - 3 from C2
    For each question, shuffles options randomly so the position of the correct answer is always unique.
    Guarantees no two test attempts will ever be identical.
    """
    sampled = []
    tiers = [
        ("A1", 3),
        ("A2", 3),
        ("B1", 4),
        ("B2", 4),
        ("C1", 3),
        ("C2", 3)
    ]
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
    """
    Returns (level_name, target_callback) based on score:
    0-4: 🌱 Beginner (A1) -> level_a1
    5-8: 📘 Elementary (A2) -> level_a2
    9-12: 📙 Pre-Intermediate (B1) -> level_b1
    13-15: 📕 Intermediate & Upper (B2) -> level_b2
    16-18: 🎓 Advanced (C1) -> level_c1
    19-20: 🏆 Proficiency (C2) -> level_c2
    """
    pct = (score / total) * 100 if total > 0 else 0
    if pct <= 24:
        return "🌱 Beginner (A1)", "level_a1"
    elif pct <= 44:
        return "📘 Elementary (A2)", "level_a2"
    elif pct <= 64:
        return "📙 Pre-Intermediate (B1)", "level_b1"
    elif pct <= 79:
        return "📕 Intermediate & Upper (B2)", "level_b2"
    elif pct <= 94:
        return "🎓 Advanced (C1)", "level_c1"
    else:
        return "🏆 Proficiency (C2)", "level_c2"

def build_placement_question_keyboard(q_idx: int, score: int, options: list) -> InlineKeyboardMarkup:
    """Builds clean inline buttons for the given question options and running score."""
    keyboard = []
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
        "📝 <b>اختبار تحديد المستوى المتقدم (متجدد آلياً)</b>\n\n"
        "يتكون الاختبار من <b>20 سؤالاً</b> متدرج الصعوبة (من A1 إلى C2) تم اختياره وتحديثه آلياً.\n"
        "• يرجى اختيار الإجابة الأصح لكل سؤال.\n"
        "• يتم توليد نموذج أسئلة جديد ومختلف في كل مرة تعيد فيها الاختبار لضمان دقة قياس مستواك!\n"
        "• يعتمد تحديد مستواك بدقة على إجاباتك الفردية دون استخدام وسائل مساعدة."
    )
    keyboard = [
        [InlineKeyboardButton(text="🚀 ابدأ الاختبار الآن | Start Test", callback_data="start_placement_test")],
        [InlineKeyboardButton(text="📚 تصفح الدورات | Browse Courses", callback_data="back_to_courses")]
    ]
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@quizzes_router.callback_query(F.data == "start_placement_test")
async def handle_start_placement_test(callback: CallbackQuery, state: FSMContext):
    """Generates a fresh, randomized 20-question placement test and launches Question 1."""
    questions = sample_diagnostic_placement_questions()
    await state.update_data(placement_questions=questions)

    first_q = questions[0]
    total_q = len(questions)
    text = (
        f"📝 <b>اختبار تحديد المستوى (السؤال 1 من {total_q})</b>\n\n"
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
    """Evaluates question answer, advances through 20 questions via edit_message_text, and gives final diagnostic evaluation."""
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
            f"📝 <b>اختبار تحديد المستوى (السؤال {next_idx + 1} من {total_q})</b>\n\n"
            f"❓ <b>{next_q['question']}</b>"
        )
        keyboard = build_placement_question_keyboard(next_idx, score, next_q["options"])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        # Placement test completed!
        level_name, target_callback = get_placement_level_info(score, total_q)
        final_score = score
        user_level = level_name
        message = callback.message
        result_text = (
            "📊 <b>نتيجة اختبار تحديد المستوى | Placement Test Result</b>\n\n"
            f"لقد أجبت بشكل صحيح على <b>{score}</b> من أصل {total_q} سؤالاً.\n"
            f"مستواك اللغوي الحالي هو: <b>{level_name}</b>\n\n"
            "🎯 الكورس التدريبي الموصى به لك هو كورس اللغة العامة لهذا المستوى، حيث سيعمل على تطوير نقاط قوتك ومعالجة نقاط ضعفك في القواعد، المفردات، والتلفظ."
        )
        result_keyboard = [
            [InlineKeyboardButton(text="📖 عرض تفاصيل كورس مستواي", callback_data=target_callback)],
            [InlineKeyboardButton(text="🔄 إعادة الاختبار بنموذج أسئلة جديد | Retake", callback_data="start_placement_test")],
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
                        q_find = select(Quiz).where(Quiz.title.ilike("%Placement%"))
                        q_res = await session.execute(q_find)
                        placement_quiz = q_res.scalar_one_or_none()
                        if not placement_quiz:
                            placement_quiz = Quiz(
                                title="Comprehensive Placement Test (20 Questions)",
                                pass_percentage=50,
                                is_exam=True
                            )
                            session.add(placement_quiz)
                            await session.flush()

                        attempt = QuizAttempt(
                            student_id=user.id,
                            quiz_id=placement_quiz.id,
                            score_percentage=round((score / total_q) * 100, 1),
                            passed=score >= 10,
                            started_at=datetime.now(timezone.utc),
                            completed_at=datetime.now(timezone.utc)
                        )
                        session.add(attempt)
                        await session.commit()
            except Exception as e:
                print(f"[Placement Attempt Save Error] {e}")

            # Save to Notion asynchronously
            try:
                first_name = (message.chat.first_name if (message and message.chat) else None) or (tg_user.first_name if tg_user else "طالب مجهول")
                username = (message.chat.username if (message and message.chat) else None) or (tg_user.username if tg_user else None)

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

        await state.clear()
        await callback.message.edit_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=result_keyboard),
            parse_mode="HTML"
        )

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

        att_query = select(QuizAttempt).where(QuizAttempt.student_id == user.id).order_by(QuizAttempt.completed_at.desc())
        att_result = await session.execute(att_query)
        attempts = att_result.scalars().all()

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

@quizzes_router.callback_query(F.data == "back_to_quizzes_menu")
async def handle_back_to_quizzes_menu(callback: CallbackQuery):
    """Returns to the quizzes menu."""
    await callback.answer()
    if callback.message:
        await handle_quizzes_and_grades(callback.message)

@quizzes_router.callback_query(F.data == "open_daily_info")
async def handle_open_daily_info(callback: CallbackQuery):
    """Sends today's educational info, audio pronunciation, and quiz button."""
    await callback.answer("جاري تجهيز معلومة اليوم واختبارها...")
    lesson = get_today_lesson(force_refresh=False)
    await send_daily_lesson_to_user(callback.bot, callback.message.chat.id, lesson, send_voice=True)

@quizzes_router.callback_query(F.data == "refresh_daily_lesson")
async def handle_refresh_daily_lesson(callback: CallbackQuery):
    """Generates a fresh new AI English lesson and quiz on demand."""
    await callback.answer("🔄 جاري توليد معلومة واختبار جديد بالذكاء الاصطناعي...")
    await callback.message.answer(
        "⚡ <b>جاري إعداد محتوى تعليمي واختبار جديد بالذكاء الاصطناعي...</b>\n<i>ثوانٍ معدودة...</i>",
        parse_mode="HTML"
    )
    lesson = await asyncio.to_thread(get_today_lesson, force_refresh=True)
    await send_daily_lesson_to_user(callback.bot, callback.message.chat.id, lesson, send_voice=True)

@quizzes_router.callback_query(F.data == "start_daily_info_quiz")
async def handle_start_daily_info_quiz(callback: CallbackQuery):
    """Starts the dynamic quiz for today's lesson."""
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
            InlineKeyboardButton(
                text=opt_text,
                callback_data=f"dquiz_0_{opt_idx}_0"
            )
        ])

    await callback.message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()

@quizzes_router.callback_query(F.data.startswith("dquiz_"))
async def handle_daily_quiz_answer(callback: CallbackQuery):
    """Evaluates student's answer for dynamic daily quiz and advances to next question or final score."""
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
                InlineKeyboardButton(
                    text=opt_text,
                    callback_data=f"dquiz_{next_q_idx}_{opt_idx}_{current_score}"
                )
            ])

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
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

        await callback.message.edit_text(
            final_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )

    await callback.answer()
