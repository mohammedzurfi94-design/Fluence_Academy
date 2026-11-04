from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from sqlalchemy import select
from pathlib import Path

from app.database.connection import AsyncSessionLocal
from app.database.models import User, Course, Lesson, LessonMaterial, Enrollment, StudentProgress
from app.bot.keyboards.main_menu import (
    get_channel_join_keyboard,
    get_courses_catalog_keyboard,
    get_general_english_keyboard,
    get_academic_english_keyboard,
    get_exam_details_keyboard,
    get_sub_level_keyboard
)
from app.services.channel_service import check_user_channel_membership
from app.core.config import settings

courses_router = Router(name="courses_router")

# ---------------------------------------------------------------------------
# 1. Main Courses Catalog Handler
# ---------------------------------------------------------------------------
@courses_router.message(F.text.in_(["📚 الدورات التدريبية | Courses", "📚 Browse Courses"]))
async def handle_courses_catalog_message(message: Message):
    """Displays the main courses catalog with interactive inline categories."""
    text = (
        "📚 <b>أكاديمية Fluence للغة الإنجليزية | دليل الدورات التدريبية</b>\n\n"
        "مرحباً بك في القسم الأكاديمي المتكامل. تم تصميم برامجنا التعليمية بعناية "
        "لتلبي احتياجات مختلف المستويات والتخصصات.\n\n"
        "اختر المسار الذي تود استكشافه أو الانضمام إليه من القائمة أدناه: 👇"
    )
    await message.answer(text, reply_markup=get_courses_catalog_keyboard(), parse_mode="HTML")

@courses_router.callback_query(F.data == "back_to_courses")
async def handle_back_to_courses(callback: CallbackQuery):
    """Returns to the main courses catalog."""
    text = (
        "📚 <b>أكاديمية Fluence للغة الإنجليزية | دليل الدورات التدريبية</b>\n\n"
        "مرحباً بك في القسم الأكاديمي المتكامل. تم تصميم برامجنا التعليمية بعناية "
        "لتلبي احتياجات مختلف المستويات والتخصصات.\n\n"
        "اختر المسار الذي تود استكشافه أو الانضمام إليه من القائمة أدناه: 👇"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_courses_catalog_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_courses_catalog_keyboard(), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data == "back_to_main_menu")
async def handle_back_to_main_menu(callback: CallbackQuery):
    """Provides navigation feedback to the user."""
    await callback.answer("القائمة الرئيسية متوفرة دائماً في الأسفل 👇", show_alert=False)

# ---------------------------------------------------------------------------
# 2. General English Hierarchy (Levels A1, A2, B1, B2)
# ---------------------------------------------------------------------------
@courses_router.callback_query(F.data == "cat_general")
async def handle_cat_general(callback: CallbackQuery):
    """Displays General English level selection."""
    text = (
        "🗣️ <b>كورسات اللغة الإنجليزية العامة | General English</b>\n\n"
        "سلسلة تدريبية متكاملة تهدف إلى بناء طلاقتك التعبيرية والشفهية وتطوير مهارات "
        "المحادثة، الاستماع، القواعد، والنطق السليم خطوة بخطوة وفق الإطار الأوروبي المشترك (CEFR).\n\n"
        "اختر مستواك المطلوب لمعرفة التفاصيل والبدء: 👇"
    )
    await callback.message.edit_text(text, reply_markup=get_general_english_keyboard(), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data == "level_a1")
async def handle_level_a1(callback: CallbackQuery):
    text = (
        "🌱 <b>المستوى المبتدئ | Beginner (A1)</b>\n\n"
        "📌 <b>لمن هذا المستوى؟</b>\n"
        "للطلبة الذين يبدأون رحلتهم في تعلم اللغة الإنجليزية من الصفر أو يرغبون بتثبيت الأساسيات.\n\n"
        "🎯 <b>أهم المخرجات والمهارات:</b>\n"
        "• إتقان الحروف والأصوات الإنجليزية والتهجئة الدقيقة.\n"
        "• تكوين الجمل البسيطة والتحدث في المواقف الروتينية اليومية.\n"
        "• مفردات الحياة الأساسية (التعريف بالنفس، العائلة، العمل، الأرقام والوقت).\n"
        "• مهارات القراءة للملصقات والرسائل القصيرة والمحادثة المبتدئة."
    )
    await callback.message.edit_text(text, reply_markup=get_sub_level_keyboard("cat_general"), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data == "level_a2")
async def handle_level_a2(callback: CallbackQuery):
    text = (
        "📘 <b>المستوى الأساسي | Elementary (A2)</b>\n\n"
        "📌 <b>لمن هذا المستوى؟</b>\n"
        "للطلبة الذين يمتلكون المعرفة الأولية ويرغبون في التحدث بجمل مترابطة وبناء ثقة أكبر.\n\n"
        "🎯 <b>أهم المخرجات والمهارات:</b>\n"
        "• ضبط الأزمنة الأساسية: الماضي، الحاضر المستمر، والمستقبل.\n"
        "• التواصل الفعال في السفر، المقاهي، الأسواق، والمطارات.\n"
        "• التعبير عن التجارب السابقة والخطط المستقبلية والاهتمامات الشخصية.\n"
        "• الاستماع للمحادثات القصيرة وفهم النقاط الجوهرية منها بسهولة."
    )
    await callback.message.edit_text(text, reply_markup=get_sub_level_keyboard("cat_general"), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data == "level_b1")
async def handle_level_b1(callback: CallbackQuery):
    text = (
        "📈 <b>المستوى قبل المتوسط | Pre-Intermediate (B1)</b>\n\n"
        "📌 <b>لمن هذا المستوى؟</b>\n"
        "لمن يسعى للتخلص من التردد والترجمة الذهنية وبدء التحدث بطلاقة وتلقائية طبيعية.\n\n"
        "🎯 <b>أهم المخرجات والمهارات:</b>\n"
        "• التعامل بمرونة مع معظم المواقف اليومية في بيئة العمل والدراسة.\n"
        "• استخدام القواعد المركبة وحروف الربط لتشكيل نقاش متصل.\n"
        "• التعبير عن الآراء، المشاعر، وتفسير أسباب القرارات الشخصية.\n"
        "• فهم الحوارات والمقاطع الصوتية ذات السرعة الطبيعية."
    )
    await callback.message.edit_text(text, reply_markup=get_sub_level_keyboard("cat_general"), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data == "level_b2")
async def handle_level_b2(callback: CallbackQuery):
    text = (
        "🏆 <b>المستوى المتقدم | Intermediate & Upper (B2)</b>\n\n"
        "📌 <b>لمن هذا المستوى؟</b>\n"
        "للوصول إلى مرحلة الاستقلال اللغوي الكامل والجاهزية المهنية والأكاديمية العالية.\n\n"
        "🎯 <b>أهم المخرجات والمهارات:</b>\n"
        "• التفاعل بعفوية وسرعة مع المتحدثين الأصليين دون جهد أو تلعثم.\n"
        "• كتابة المقالات التفصيلية وإعداد التقارير الاحترافية.\n"
        "• فهم الأفكار الرئيسية في النصوص المعقدة ومناقشة المواضيع الفكرية.\n"
        "• إتقان التعبيرات الاصطلاحية (Idioms) والمفردات المتقدمة."
    )
    await callback.message.edit_text(text, reply_markup=get_sub_level_keyboard("cat_general"), parse_mode="HTML")
    await callback.answer()

# ---------------------------------------------------------------------------
# 3. Academic English Hierarchy (Writing, Presentations, Pronunciation)
# ---------------------------------------------------------------------------
@courses_router.callback_query(F.data == "cat_academic")
async def handle_cat_academic(callback: CallbackQuery):
    """Displays Academic English tracks selection."""
    text = (
        "🏛️ <b>كورسات اللغة الأكاديمية | Academic English</b>\n\n"
        "برامج تخصصية احترافية موجهة لطلبة الدراسات العليا، الباحثين، وأعضاء الهيئات التدريسية "
        "لتمكينهم من المعايير البحثية الدولية في الصياغة والإلقاء العلمي.\n\n"
        "اختر المسار الأكاديمي المطلوب: 👇"
    )
    await callback.message.edit_text(text, reply_markup=get_academic_english_keyboard(), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data == "acad_writing")
async def handle_acad_writing(callback: CallbackQuery):
    text = (
        "✍️ <b>الكتابة الأكاديمية والبحوث | Academic Writing & Research</b>\n\n"
        "📌 <b>محاور المسار التدريبي:</b>\n"
        "• هيكلة الأوراق البحثية، رسائل الماجستير، وأطاريح الدكتوراه وفق أحدث المعايير.\n"
        "• صياغة الملخصات (Abstracts)، المقدمة، ومراجعة الأدبيات (Literature Review).\n"
        "• أساليب التوثيق المعتمدة عالمياً (APA, Harvard, IEEE, Chicago).\n"
        "• تقنيات إعادة الصياغة (Paraphrasing) المتقنة وتجنب الاستلال والسرقة الأدبية (Plagiarism).\n"
        "• استخدام العبارات الانتقالية والروابط الأكاديمية الاحترافية (Signposting)."
    )
    await callback.message.edit_text(text, reply_markup=get_sub_level_keyboard("cat_academic"), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data == "acad_presentations")
async def handle_acad_presentations(callback: CallbackQuery):
    text = (
        "🎤 <b>مهارات العرض والإلقاء | Academic Presentations</b>\n\n"
        "📌 <b>محاور المسار التدريبي:</b>\n"
        "• إعداد وتصميم شرائح العرض العلمي (Slides) بطريقة جذابة ومختصرة.\n"
        "• أسلوب الخطاب الأكاديمي ولغة الجسد الاحترافية في المؤتمرات والندوات والسمينارات.\n"
        "• فن التحدث أمام لجان المناقشة وإدارة جلسات الأسئلة والأجوبة (Q&A) بكل ثقة وهدوء.\n"
        "• التحكم بنبرة الصوت وتوصيل الفكرة البحثية بأعلى وضوح ممكن."
    )
    await callback.message.edit_text(text, reply_markup=get_sub_level_keyboard("cat_academic"), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data == "acad_phonetics")
async def handle_acad_phonetics(callback: CallbackQuery):
    text = (
        "🗣️ <b>النطق والتجويد اللفظي | Pronunciation & Phonetics</b>\n\n"
        "📌 <b>محاور المسار التدريبي:</b>\n"
        "• دراسة مخارج الحروف الإنجليزية والرموز الصوتية العالمية (IPA).\n"
        "• نبر الكلمات والجمل (Word Stress & Sentence Stress) لإعطاء المعنى الصحيح.\n"
        "• التنغيم (Intonation) والربط الصوتي الطبيعي بين الكلمات (Connected Speech).\n"
        "• معالجة الأخطاء الشائعة في النطق العربي وتحقيق مخارج صوتية واضحة ومريحة."
    )
    await callback.message.edit_text(text, reply_markup=get_sub_level_keyboard("cat_academic"), parse_mode="HTML")
    await callback.answer()

# ---------------------------------------------------------------------------
# 4. Competitive Exam & INELT (National Exam) Handlers
# ---------------------------------------------------------------------------
@courses_router.callback_query(F.data == "course_competitive")
async def handle_course_competitive(callback: CallbackQuery):
    """Displays detailed overview for the Competitive Exam with direct contact button."""
    text = (
        "🎯 <b>كورس الامتحان التنافسي للدراسات العليا | Competitive Exam</b>\n\n"
        "برنامج تدريبي مكثف مخصص للطلبة المتقدمين للامتحان التنافسي للقبول في الدراسات العليا "
        "(دبلوم عالي، ماجستير، دكتوراه) في كافة الجامعات العراقية.\n\n"
        "📌 <b>أهم محاور ومميزات الدورة:</b>\n"
        "• تحليل شامل للنماذج الوزارية المعتمدة وأسئلة الامتحانات التنافسية للأعوام السابقة.\n"
        "• تدريب مكثف على مهارات القواعد والتركيب اللغوي (Grammar & Structure).\n"
        "• استراتيجيات حل نصوص القراءة السريعة واكتشاف الإجابات الدقيقة (Reading Comprehension).\n"
        "• اختبارات إلكترونية تجريبية تفاعلية تحاكي ضغط ونظام الاختبار الحقيقي.\n"
        "• مذكرات وملازم وملخصات حصرية وشاملة للمشاركين.\n\n"
        "👨‍🏫 <b>إشراف وتدريس:</b> الأستاذ محمد حسين\n\n"
        "للحجز والاستفسار عن موعد انطلاق الدورة والاشتراك المباشر، تواصل معنا عبر الزر أدناه: 👇"
    )
    await callback.message.edit_text(text, reply_markup=get_exam_details_keyboard("https://t.me/Alzurfi1"), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data == "course_inelt")
async def handle_course_inelt(callback: CallbackQuery):
    """Displays detailed overview for the INELT National Exam with direct contact button."""
    text = (
        "🇮🇶 <b>كورس الاختبار الوطني للغة الإنجليزية (INELT) | National Exam</b>\n\n"
        "الدورة التخصصية الذهبية لاجتياز اختبار اللغة الإنجليزية الوطني الموحد والمعتمد رسمياً "
        "من وزارة التعليم العالي والبحث العلمي كشرط للتقديم للدراسات العليا والترقيات العلمية.\n\n"
        "📌 <b>أهم محاور الدورة:</b>\n"
        "• تدريب دقيق على أقسام الاختبار الثلاثة: الاستماع (Listening)، القواعد (Structure)، والقراءة (Reading).\n"
        "• استراتيجيات إدارة الوقت الذكية واكتشاف الإجابات الصحيحة في أقل وقت ممكن.\n"
        "• حل بنك الأسئلة المعتمد ونماذج حقيقية مطابقة للبيئة الحاسوبية للاختبار الوطني.\n"
        "• ملخصات وقوالب تركيز معتمدة تضمن للمشارك تحقيق الدرجة المطلوبة للتخصص.\n\n"
        "👨‍🏫 <b>إشراف وتدريس:</b> الأستاذ محمد حسين\n\n"
        "للتسجيل والاستفسار عن تفاصيل المقاعد المتاحة، اضغط على زر التواصل مع الإدارة أدناه: 👇"
    )
    await callback.message.edit_text(text, reply_markup=get_exam_details_keyboard("https://t.me/Alzurfi1"), parse_mode="HTML")
    await callback.answer()

# ---------------------------------------------------------------------------
# 5. Browse Lessons from Database & Lesson Reader
# ---------------------------------------------------------------------------
@courses_router.callback_query(F.data.in_(["browse_available_lessons", "back_to_catalog"]))
async def handle_browse_lessons_from_db(callback: CallbackQuery):
    """Lists published courses from the database."""
    async with AsyncSessionLocal() as session:
        query = select(Course).where(Course.is_published == True)
        result = await session.execute(query)
        courses = result.scalars().all()

    if not courses:
        text = (
            "📚 <b>الدروس التفاعلية | Lessons</b>\n\n"
            "يتم حالياً تجهيز ورفع الدروس التفاعلية الجديدة من قبل الأستاذ محمد حسين.\n"
            "تابع قناة الأكاديمية الرسمية لتصلك الإشعارات فور توفرها! 🌟"
        )
        keyboard = [[InlineKeyboardButton(text="🔙 رجوع | Back", callback_data="back_to_courses")]]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        await callback.answer()
        return

    text = "📚 <b>الدروس والمناهج المتاحة حالياً | Available Courses:</b>\n\nاختر الكورس لعرض قائمة الدروس والبدء:"
    keyboard = []
    for c in courses:
        keyboard.append([InlineKeyboardButton(text=f"🎓 {c.title}", callback_data=f"view_course_{c.id}")])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع | Back", callback_data="back_to_courses")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

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
        f"{course.description or 'دورة تعليمية شاملة ومقدمة بأعلى المعايير الأكاديمية.'}\n\n"
        f"📖 <b>فهرس الدروس المتاحة ({len(lessons)} درس):</b>\n"
    )

    keyboard = []
    for l in lessons:
        preview_tag = "🆓 " if l.is_preview else "📖 "
        keyboard.append([InlineKeyboardButton(text=f"{preview_tag}{l.title}", callback_data=f"read_lesson_{l.id}")])

    keyboard.append([InlineKeyboardButton(text="🔙 رجوع | Back", callback_data="browse_available_lessons")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()

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
            await callback.answer("الدرس غير موجود.", show_alert=True)
            return

        # Check channel gatekeeper
        is_member, _ = await check_user_channel_membership(bot, user_id)
        if not is_member and not lesson.is_preview:
            channel = settings.REQUIRED_TELEGRAM_CHANNEL or "@FluenceEnglish"
            clean_ch = channel.replace("@", "")
            await callback.message.answer(
                f"🔒 <b>عذراً، محتوى هذا الدرس مخصص للمشتركين</b>\n\n"
                f"لفتح درس <b>{lesson.title}</b> وكافة محتويات الأكاديمية، يرجى الانضمام لقناتنا الرسمية أولاً: <b>{channel}</b>!",
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
        keyboard.append([InlineKeyboardButton(text=f"📄 تحميل {mat.title}", callback_data=f"get_mat_{mat.id}")])

    keyboard.append([InlineKeyboardButton(text="📝 أداء اختبار الدرس | Take Quiz", callback_data=f"start_quiz_{lesson.id}")])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع للدروس | Back", callback_data=f"view_course_{lesson.course_id}")])

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
        await callback.answer("ملف المادة غير متوفر حالياً على الخادم.", show_alert=True)
        return

    await callback.answer("جارٍ إرسال الملف...")
    pdf_file = FSInputFile(material.file_path, filename=material.title)
    await callback.message.answer_document(
        document=pdf_file,
        caption=f"📄 <b>{material.title}</b>\nFluence Academy Study Resource",
        parse_mode="HTML"
    )

# ---------------------------------------------------------------------------
# 6. Study Files & Materials Library Handler
# ---------------------------------------------------------------------------
@courses_router.message(F.text.in_(["📁 الملفات والمواد | Study Files & Materials"]))
async def handle_study_materials_library(message: Message):
    """Displays the study materials library with downloadable handouts and summaries."""
    async with AsyncSessionLocal() as session:
        query = select(LessonMaterial).limit(10)
        result = await session.execute(query)
        materials = result.scalars().all()

    text = (
        "📁 <b>مكتبة الملفات والمواد الدراسية | Study Files & Materials</b>\n\n"
        "أهلاً بك في المكتبة الرقمية لأكاديمية Fluence.\n"
        "تجد هنا ملخصات القواعد، المذكرات التخصصية، وجداول المفردات المعتمدة الجاهزة للتحميل المباشر بصيغة PDF.\n\n"
    )

    keyboard = []
    if materials:
        text += "اختر الملف الذي تود تحميله مباشرة إلى جهازك: 👇"
        for mat in materials:
            keyboard.append([InlineKeyboardButton(text=f"📄 تحميل {mat.title}", callback_data=f"get_mat_{mat.id}")])
    else:
        text += "يتم حالياً رفع وتجهيز الحقائب والملخصات من قبل إدارة الأكاديمية. سيتم إشعاركم في القناة عند توفر كل ملف جديد!"

    keyboard.append([InlineKeyboardButton(text="📢 القناة الرسمية | Official Channel", url="https://t.me/FluenceEnglish")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
