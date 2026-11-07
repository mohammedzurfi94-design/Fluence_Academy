import random
import html
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
    get_sub_level_keyboard,
    get_library_keyboard,
    get_library_back_keyboard
)
from app.services.channel_service import check_user_channel_membership
from app.core.config import settings

courses_router = Router(name="courses_router")

# ---------------------------------------------------------------------------
# 1. Main Courses Catalog Handler
# ---------------------------------------------------------------------------
@courses_router.message(F.text.in_([
    "📚 الدورات التدريبية | Courses",
    "📚 الدورات التدريبية",
    "الدورات التدريبية",
    "الكورسات",
    "دليل الكورسات",
    "/courses"
]))
async def handle_courses_catalog_message(message: Message):
    """Entry point for the courses directory via text message or bottom menu."""
    text = (
        "📚 <b>دليل الكورسات والدورات الأكاديمية | Fluence Courses</b> 🎓\n\n"
        "المشرف العام: <b>Lect. Mohammed Hussein</b>\n\n"
        "اختر المسار التعليمي أو التخصصي الذي يناسب هدفك الأكاديمي:\n\n"
        "• 🏛️ <b>كورسات اللغة الأكاديمية:</b> مخصصة للدراسات العليا والأبحاث والمناقشات.\n"
        "• 🗣️ <b>كورسات اللغة العامة:</b> لكافة المستويات من A1 حتى إتقان C2.\n"
        "• 🎯 <b>محاكي وكورس الامتحان التنافسي:</b> للمتقدمين للماجستير والدكتوراه.\n"
        "• 🇮🇶 <b>محاكي وكورس الاختبار الوطني (INELT):</b> لاجتياز اختبار الكفاءة الوزاري.\n\n"
        "👇 <b>اضغط على القسم المطلوب لاستعراض محاوره وتفاصيله:</b>"
    )
    await message.answer(text, reply_markup=get_courses_catalog_keyboard(), parse_mode="HTML")

@courses_router.callback_query(F.data.in_(["back_to_courses", "show_courses_catalog"]))
async def handle_courses_catalog_callback(callback: CallbackQuery):
    """Displays the courses directory when navigating back from other sections."""
    text = (
        "📚 <b>دليل الكورسات والدورات الأكاديمية | Fluence Courses</b> 🎓\n\n"
        "المشرف العام: <b>Lect. Mohammed Hussein</b>\n\n"
        "اختر المسار التعليمي أو التخصصي الذي يناسب هدفك الأكاديمي:\n\n"
        "• 🏛️ <b>كورسات اللغة الأكاديمية:</b> مخصصة للدراسات العليا والأبحاث والمناقشات.\n"
        "• 🗣️ <b>كورسات اللغة العامة:</b> لكافة المستويات من A1 حتى إتقان C2.\n"
        "• 🎯 <b>محاكي وكورس الامتحان التنافسي:</b> للمتقدمين للماجستير والدكتوراه.\n"
        "• 🇮🇶 <b>محاكي وكورس الاختبار الوطني (INELT):</b> لاجتياز اختبار الكفاءة الوزاري.\n\n"
        "👇 <b>اضغط على القسم المطلوب لاستعراض محاوره وتفاصيله:</b>"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_courses_catalog_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_courses_catalog_keyboard(), parse_mode="HTML")
    await callback.answer()

# ---------------------------------------------------------------------------
# 2. General English Tracks
# ---------------------------------------------------------------------------
@courses_router.callback_query(F.data == "cat_general")
async def handle_cat_general(callback: CallbackQuery):
    text = (
        "🗣️ <b>كورسات اللغة الإنجليزية العامة | General English Tracks</b>\n\n"
        "تغطي السلسلة كافة المستويات وفق الإطار الأوروبي المرجعي المشترك (CEFR):\n\n"
        "🌱 <b>A1 - المبتدئ:</b> بناء الأساس اللغوي والمفردات الأولية.\n"
        "📘 <b>A2 - الأساسي:</b> التراكيب اللغوية الأساسية والمحادثات اليومية.\n"
        "📙 <b>B1 - قبل المتوسط:</b> التعبير بطلاقة وتطوير مهارات القراءة والاستماع.\n"
        "📕 <b>B2 - المتوسط المتقدم:</b> الاستخدام التلقائي وتوسيع التراكيب المعقدة.\n"
        "🎓 <b>C1 - المتقدم:</b> اللغة التخصصية والمناقشات الفكرية والمهنية.\n"
        "🏆 <b>C2 - الإتقان التام:</b> الطلاقة المماثلة للناطقين الأصليين باللغة.\n\n"
        "اختر مستواك المطلوب للاطلاع على تفاصيل الكورس:"
    )
    await callback.message.edit_text(text, reply_markup=get_general_english_keyboard(), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data.startswith("level_"))
async def handle_general_level_details(callback: CallbackQuery):
    level_code = callback.data.split("_")[-1].upper()
    level_names = {
        "A1": "🌱 المستوى المبتدئ (A1 - Starter)",
        "A2": "📘 المستوى الأساسي (A2 - Elementary)",
        "B1": "📙 المستوى قبل المتوسط (B1 - Pre-Intermediate)",
        "B2": "📕 المستوى المتوسط وفوق المتوسط (B2 - Intermediate)",
        "C1": "🎓 المستوى المتقدم (C1 - Advanced)",
        "C2": "🏆 مستوى الإتقان التام (C2 - Proficiency)"
    }
    title = level_names.get(level_code, f"المستوى {level_code}")
    text = (
        f"<b>{title}</b>\n\n"
        f"يشمل هذا الكورس تدريباً تفاعلياً مكثفاً يغطي:\n"
        f"• المحاضرات المسجلة والمباشرة وتدريبات النطق واللكنة البريطانية.\n"
        f"• واجبات دورية وتصحيح تفاعلي بواسطة الذكاء الاصطناعي وإشراف الأستاذ.\n"
        f"• اختبارات أسبوعية لتقييم التقدم وحفظ النتائج في السجل الأكاديمي.\n\n"
        f"للتسجيل والاستفسار عن تفاصيل الاشتراك، اضغط على زر التواصل مع الأستاذ أدناه:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_sub_level_keyboard(parent_back="cat_general", browse_callback="browse_available_lessons"),
        parse_mode="HTML"
    )
    await callback.answer()

# ---------------------------------------------------------------------------
# 3. Academic English Tracks
# ---------------------------------------------------------------------------
@courses_router.callback_query(F.data == "cat_academic")
async def handle_cat_academic(callback: CallbackQuery):
    text = (
        "🏛️ <b>كورسات اللغة الإنجليزية الأكاديمية | Academic English</b>\n\n"
        "مصممة لطلبة الدراسات العليا (الدبلوم العالي، الماجستير، الدكتوراه) والباحثين:\n\n"
        "✍️ <b>الكتابة الأكاديمية والبحوث:</b> صياغة ملخصات البحوث (Abstracts) والأطروحات.\n"
        "🎤 <b>مهارات العرض والإلقاء:</b> الدفاع عن الأطروحة والمشاركات في المؤتمرات الدولية.\n"
        "🗣️ <b>النطق والتجويد اللفظي:</b> التلفظ الصوتي المعتمد (Phonetics & Phonology).\n\n"
        "اختر المسار للاطلاع على محاور الدورة:"
    )
    await callback.message.edit_text(text, reply_markup=get_academic_english_keyboard(), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data.in_(["acad_writing", "acad_presentations", "acad_phonetics"]))
async def handle_academic_subtracks(callback: CallbackQuery):
    sub = callback.data
    if sub == "acad_writing":
        name = "✍️ الكتابة الأكاديمية والبحوث (Academic Writing & Research)"
        desc = "• صياغة المقدمة والفرضيات وتوثيق المصادر (APA/MLA/Chicago).\n• تفادي الاستلال العلمي (Plagiarism) وتطوير الأسلوب الأكاديمي الرصين."
    elif sub == "acad_presentations":
        name = "🎤 مهارات العرض والإلقاء (Academic Presentations)"
        desc = "• مهارات الدفاع عن أطروحة الماجستير أو الدكتوراه أمام اللجان العلمية.\n• استخدام لغة الجسد وتصميم الشرائح الأكاديمية الاحترافية."
    else:
        name = "🗣️ النطق والتجويد اللفظي (Phonetics & Phonology)"
        desc = "• دراسة مخارج الحروف والمقاطع الصوتية وفق اللكنة البريطانية المعتمدة (RP).\n• التجويد اللفظي، التشديد (Stress)، والنغمات الصوتية (Intonation)."

    text = (
        f"<b>{name}</b>\n\n"
        f"<b>محاور البرنامج:</b>\n"
        f"{desc}\n\n"
        f"📩 <b>للاستفسار عن مواعيد الدورة القادمة والحجز:</b>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_sub_level_keyboard(parent_back="cat_academic", browse_callback="browse_available_lessons"),
        parse_mode="HTML"
    )
    await callback.answer()

# ---------------------------------------------------------------------------
# 4. Competitive Exam & INELT (National Exam) Interactive Simulators
# ---------------------------------------------------------------------------

COMPETITIVE_QUESTIONS_POOL = [
    {
        "q": "In Shakespearean Tragedy, which term describes the fatal flaw or error in judgment that leads to the downfall of the tragic hero?",
        "opts": ["Hamartia", "Catharsis", "Peripeteia", "Anagnorisis"],
        "c": 0,
        "exp": "مصطلح <b>Hamartia</b> (من النقد الأرسطي) يشير إلى الخلل المأساوي أو الخطأ التقديري للبطل التراجيدي (مثل تردد هاملت أو طموح ماكبث)."
    },
    {
        "q": "Which critical approach is associated with Jacques Derrida's famous assertion: 'There is nothing outside the text' (Il n'y a pas de hors-texte)?",
        "opts": ["Deconstruction", "New Historicism", "Psychoanalytic Criticism", "Marxist Criticism"],
        "c": 0,
        "exp": "مقولة دريدا الشهيرة تمثل جوهر <b>التفكيكية (Deconstruction)</b>، حيث ترى أن اللغة غير مستقرة ولا يوجد معنى نهائي مطلق خارج النص."
    },
    {
        "q": "T.S. Eliot formulated which concept in 'Hamlet and His Problems' to describe creating an artistic formula for a specific emotion?",
        "opts": ["Objective Correlative", "Negative Capability", "Dissociation of Sensibility", "Epiphany"],
        "c": 0,
        "exp": "المتلازم الموضوعي <b>(Objective Correlative)</b> صاغه ت. س. إليوت لوصف إيجاد أحداث ومواقف مادية لتكون معادلاً للتعبير عن عاطفة معينة."
    },
    {
        "q": "Which literary narrative technique represents the continuous, unstructured flow of conscious thoughts and associations in a character's mind?",
        "opts": ["Stream of Consciousness", "Verisimilitude", "Allegory", "Picaresque"],
        "c": 0,
        "exp": "تقنية <b>تيار الوعي (Stream
