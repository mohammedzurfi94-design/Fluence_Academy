import asyncio
from pathlib import Path
from sqlalchemy import select
from app.database.connection import engine, Base, AsyncSessionLocal
from app.database.models import (
    User, Course, Lesson, LessonMaterial, Quiz, QuizQuestion, QuizAnswer
)
from app.core.config import settings
from app.core.security import hash_password

async def init_database():
    """Initializes tables and creates default admin account if not present."""
    # Ensure storage directories exist
    base_dir = Path(__file__).resolve().parent.parent.parent
    (base_dir / "storage" / "pdfs").mkdir(parents=True, exist_ok=True)
    (base_dir / "storage" / "backups").mkdir(parents=True, exist_ok=True)

    # Create all tables defined in models.py
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create default admin account if not already existing
    async with AsyncSessionLocal() as session:
        query = select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME)
        result = await session.execute(query)
        admin = result.scalar_one_or_none()

        if not admin:
            admin_user = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                full_name="Academy Administrator",
                hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                role="admin",
                is_active=True
            )
            session.add(admin_user)
            await session.commit()
            print(f"[Database] Default Admin created: username='{settings.DEFAULT_ADMIN_USERNAME}'")
        else:
            print("[Database] Admin account already present.")

        # Seed sample starter course if no courses exist
        course_query = select(Course)
        course_result = await session.execute(course_query)
        existing_course = course_result.scalars().first()

        if not existing_course:
            sample_course = Course(
                title="English Fluency Foundation",
                description="Master everyday conversational English, core grammar structures, and speaking confidence.",
                is_published=True,
                requires_subscription=False,
                required_telegram_channel=settings.REQUIRED_TELEGRAM_CHANNEL or "@FluenceEnglish"
            )
            session.add(sample_course)
            await session.flush()

            # Lesson 1
            lesson1 = Lesson(
                course_id=sample_course.id,
                title="1. Essential Greetings & Introductions",
                order_index=1,
                content_text=(
                    "👋 <b>Lesson 1: Essential Greetings & Introductions</b>\n\n"
                    "In English, first impressions matter! Let's master the fundamentals:\n\n"
                    "<b>1. Formal Greetings (Work, Interviews, Academics):</b>\n"
                    "• <i>'Good morning / Good afternoon'</i>\n"
                    "• <i>'Pleased to meet you.'</i>\n"
                    "• <i>'How do you do?'</i>\n\n"
                    "<b>2. Casual Greetings (Friends, Peers):</b>\n"
                    "• <i>'Hey! How's it going?'</i>\n"
                    "• <i>'Great to see you!'</i>\n\n"
                    "<b>💡 Pro Tip:</b> When someone says <i>'How do you do?'</i> in formal British English, the traditional reply is also <i>'How do you do?'</i>!"
                ),
                is_preview=True
            )
            session.add(lesson1)
            await session.flush()

            # Material for Lesson 1
            mat1 = LessonMaterial(
                lesson_id=lesson1.id,
                title="Lesson 1 Study Guide.pdf",
                file_type="pdf",
                file_path="storage/pdfs/Lesson1_Greetings.pdf",
                file_size_bytes=1024
            )
            session.add(mat1)

            # Quiz for Lesson 1
            quiz1 = Quiz(
                course_id=sample_course.id,
                lesson_id=lesson1.id,
                title="Lesson 1 Checkpoint Quiz",
                pass_percentage=70.0,
                is_exam=False
            )
            session.add(quiz1)
            await session.flush()

            # Q1
            q1 = QuizQuestion(
                quiz_id=quiz1.id,
                question_text="Which greeting is most appropriate in a formal job interview?",
                order_index=1,
                points=10,
                explanation="Formal settings require respectful expressions like 'Good morning, pleased to meet you.'"
            )
            session.add(q1)
            await session.flush()

            session.add_all([
                QuizAnswer(question_id=q1.id, answer_text="What's up?", is_correct=False),
                QuizAnswer(question_id=q1.id, answer_text="Good morning, pleased to meet you.", is_correct=True),
                QuizAnswer(question_id=q1.id, answer_text="Hey there!", is_correct=False),
                QuizAnswer(question_id=q1.id, answer_text="Yo!", is_correct=False),
            ])

            # Q2
            q2 = QuizQuestion(
                quiz_id=quiz1.id,
                question_text="Complete the sentence: 'It was a pleasure to ____ you.'",
                order_index=2,
                points=10,
                explanation="'To meet' is the infinitive form required after 'pleasure to'."
            )
            session.add(q2)
            await session.flush()

            session.add_all([
                QuizAnswer(question_id=q2.id, answer_text="meeting", is_correct=False),
                QuizAnswer(question_id=q2.id, answer_text="meet", is_correct=True),
                QuizAnswer(question_id=q2.id, answer_text="met", is_correct=False),
                QuizAnswer(question_id=q2.id, answer_text="meat", is_correct=False),
            ])

            # Lesson 2
            lesson2 = Lesson(
                course_id=sample_course.id,
                title="2. Present Simple & Daily Habits",
                order_index=2,
                content_text=(
                    "⏰ <b>Lesson 2: Present Simple & Daily Habits</b>\n\n"
                    "We use the Present Simple to talk about things that are always true or happen regularly:\n\n"
                    "<b>Form:</b>\n"
                    "• I / You / We / They + <b>work</b>\n"
                    "• He / She / It + <b>works</b> <i>(Always remember the -s / -es!)</i>\n\n"
                    "<b>Examples:</b>\n"
                    "• <i>'I study English every day.'</i>\n"
                    "• <i>'She drinks coffee in the morning.'</i>\n"
                    "• <i>'They live in London.'</i>"
                ),
                is_preview=False
            )
            session.add(lesson2)
            await session.flush()

            # Material for Lesson 2
            mat2 = LessonMaterial(
                lesson_id=lesson2.id,
                title="Lesson 2 Cheat Sheet.pdf",
                file_type="pdf",
                file_path="storage/pdfs/Lesson2_PresentSimple.pdf",
                file_size_bytes=1024
            )
            session.add(mat2)

            await session.commit()
            print("[Database] Sample course 'English Fluency Foundation' created with 2 lessons and a quiz!")

    print("[Database] All 13 tables verified and ready!")

if __name__ == "__main__":
    asyncio.run(init_database())
