from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from sqlalchemy import select
from pathlib import Path

from app.database.connection import AsyncSessionLocal
from app.database.models import User, Course, Lesson, LessonMaterial, Enrollment, StudentProgress
from app.bot.keyboards.main_menu import get_channel_join_keyboard
from app.services.channel_service import check_user_channel_membership
from app.core.config import settings

courses_router = Router(name="courses_router")

@courses_router.message(F.text == "📚 Browse Courses")
async def handle_browse_courses(message: Message):
    """Lists all available courses in Fluence Academy."""
    async with AsyncSessionLocal() as session:
        query = select(Course).where(Course.is_published == True)
        result = await session.execute(query)
        courses = result.scalars().all()

    if not courses:
        await message.answer("📚 No courses are currently published. Check back soon!")
        return

    text = "📚 <b>Fluence Academy - Course Catalog</b>\n\nSelect a course below to view syllabus and begin:"
    keyboard = []
    for c in courses:
        keyboard.append([InlineKeyboardButton(text=f"🎓 {c.title}", callback_data=f"view_course_{c.id}")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@courses_router.callback_query(F.data.startswith("view_course_"))
async def handle_view_course(callback: CallbackQuery):
    """Displays course overview and list of lessons."""
    course_id = int(callback.data.split("_")[-1])

    async with AsyncSessionLocal() as session:
        query = select(Course).where(Course.id == course_id)
        result = await session.execute(query)
        course = result.scalar_one_or_none()

        if not course:
            await callback.answer("Course not found.", show_alert=True)
            return

        # Fetch lessons
        l_query = select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.order_index)
        l_result = await session.execute(l_query)
        lessons = l_result.scalars().all()

    text = (
        f"🎓 <b>{course.title}</b>\n\n"
        f"{course.description or 'Comprehensive educational course.'}\n\n"
        f"📖 <b>Lessons Syllabus ({len(lessons)} Lessons):</b>\n"
    )

    keyboard = []
    for l in lessons:
        preview_tag = "🆓 " if l.is_preview else "📖 "
        text += f"• {l.title}\n"
        keyboard.append([InlineKeyboardButton(text=f"{preview_tag}{l.title}", callback_data=f"read_lesson_{l.id}")])

    keyboard.append([InlineKeyboardButton(text="🔙 Back to Catalog", callback_data="back_to_catalog")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )

@courses_router.callback_query(F.data == "back_to_catalog")
async def handle_back_to_catalog(callback: CallbackQuery):
    """Returns to course catalog."""
    async with AsyncSessionLocal() as session:
        query = select(Course).where(Course.is_published == True)
        result = await session.execute(query)
        courses = result.scalars().all()

    text = "📚 <b>Fluence Academy - Course Catalog</b>\n\nSelect a course below to view syllabus and begin:"
    keyboard = []
    for c in courses:
        keyboard.append([InlineKeyboardButton(text=f"🎓 {c.title}", callback_data=f"view_course_{c.id}")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )

@courses_router.callback_query(F.data.startswith("read_lesson_"))
async def handle_read_lesson(callback: CallbackQuery):
    """Displays lesson content, download button for PDFs, and quiz link."""
    lesson_id = int(callback.data.split("_")[-1])
    bot = callback.bot
    user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        l_query = select(Lesson).where(Lesson.id == lesson_id)
        l_result = await session.execute(l_query)
        lesson = l_result.scalar_one_or_none()

        if not lesson:
            await callback.answer("Lesson not found.", show_alert=True)
            return

        # Check channel gatekeeper
        is_member, _ = await check_user_channel_membership(bot, user_id)
        if not is_member and not lesson.is_preview:
            channel = settings.REQUIRED_TELEGRAM_CHANNEL or "@FluenceEnglish"
            clean_ch = channel.replace("@", "")
            await callback.message.answer(
                f"🔒 <b>Course Access Locked</b>\n\n"
                f"To access <b>{lesson.title}</b> and future lessons, please join our official channel <b>{channel}</b> first!",
                reply_markup=get_channel_join_keyboard(f"https://t.me/{clean_ch}"),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Check attached materials
        m_query = select(LessonMaterial).where(LessonMaterial.lesson_id == lesson_id)
        m_result = await session.execute(m_query)
        materials = m_result.scalars().all()

    keyboard = []
    for mat in materials:
        keyboard.append([InlineKeyboardButton(text=f"📄 Download {mat.title}", callback_data=f"get_mat_{mat.id}")])

    # Add Quiz button
    keyboard.append([InlineKeyboardButton(text="📝 Take Lesson Quiz", callback_data=f"start_quiz_{lesson.id}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Back to Course", callback_data=f"view_course_{lesson.course_id}")])

    await callback.message.answer(
        lesson.content_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()

@courses_router.callback_query(F.data.startswith("get_mat_"))
async def handle_download_material(callback: CallbackQuery):
    """Sends the PDF material directly to the student."""
    mat_id = int(callback.data.split("_")[-1])

    async with AsyncSessionLocal() as session:
        query = select(LessonMaterial).where(LessonMaterial.id == mat_id)
        result = await session.execute(query)
        material = result.scalar_one_or_none()

    if not material or not Path(material.file_path).exists():
        await callback.answer("Material file is not available on server.", show_alert=True)
        return

    await callback.answer("Sending study material...")
    pdf_file = FSInputFile(material.file_path, filename=material.title)
    await callback.message.answer_document(
        document=pdf_file,
        caption=f"📄 <b>{material.title}</b>\nFluence Academy Study Resource",
        parse_mode="HTML"
    )

@courses_router.message(F.text == "📖 My Learning")
async def handle_my_learning(message: Message):
    """Shows completed lessons and enrolled courses."""
    tg_user = message.from_user
    if not tg_user:
        return

    async with AsyncSessionLocal() as session:
        u_query = select(User).where(User.telegram_id == tg_user.id)
        u_result = await session.execute(u_query)
        user = u_result.scalar_one_or_none()

        if not user:
            await message.answer("Please type /start to register.")
            return

        # Count completed lessons
        prog_query = select(StudentProgress).where(StudentProgress.student_id == user.id)
        prog_result = await session.execute(prog_query)
        completed = prog_result.scalars().all()

    text = (
        f"📖 <b>My Learning Dashboard</b>\n\n"
        f"<b>Student:</b> {user.full_name}\n"
        f"<b>Completed Lessons:</b> {len(completed)} lesson(s)\n\n"
        f"Ready to learn more? Click <b>📚 Browse Courses</b> to continue!"
    )
    await message.answer(text, parse_mode="HTML")
