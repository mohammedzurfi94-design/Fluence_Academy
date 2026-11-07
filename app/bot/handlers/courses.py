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
        "exp": "تقنية <b>تيار الوعي (Stream of Consciousness)</b> برع فيها جيمس جويس وفرجينيا وولف لنقل التدفق الذهني المباشر دون وسيط سردي تقليدي."
    },
    {
        "q": "Select the sentence with grammatically correct academic negative inversion:",
        "opts": [
            "Not only did the researcher gather the empirical data, but he also verified it.",
            "Not only the researcher gathered the empirical data, but he also verified it.",
            "Not only did gather the researcher data, but also verified it.",
            "Not only gathered the researcher the empirical data, but he also verified it."
        ],
        "c": 0,
        "exp": "عند بدء الجملة بظرف نفي مثل <b>Not only</b> يجب تقديم الفعل المساعد على الفاعل: (did + Subject + Base Verb)."
    },
    {
        "q": "Identify the sentence that correctly avoids a dangling modifier:",
        "opts": [
            "Having completed the rigorous literature review, the scholar drafted the thesis.",
            "Having completed the rigorous literature review, the thesis was drafted by the scholar.",
            "Having completed the rigorous literature review, it was easy to draft the thesis.",
            "Having completed the rigorous literature review, drafting the thesis began."
        ],
        "c": 0,
        "exp": "لتفادي الـ <b>Dangling Modifier</b>، يجب أن يكون الاسم الذي يلي الفاصلة مباشرة هو الفاعل الحقيقي الذي أنجز المراجعة (the scholar)."
    },
    {
        "q": "William Wordsworth famously defined poetry in the Preface to 'Lyrical Ballads' as:",
        "opts": [
            "The spontaneous overflow of powerful feelings",
            "A mirror held up to human nature",
            "An imitation of an action that is serious and complete",
            "A criticism of life governed by poetic laws of truth"
        ],
        "c": 0,
        "exp": "تعريف وردزوورث الشهير في مقدمة الأغاني الغنائية (1800): 'The spontaneous overflow of powerful feelings recollected in tranquility'."
    },
    {
        "q": "The academic board recommended that the doctoral candidate _____ the revised proposal by next week.",
        "opts": ["submit", "submits", "submitted", "will submit"],
        "c": 0,
        "exp": "صيغة <b>Subjunctive</b> بعد أفعال مثل (recommend, propose, insist) تفرض استخدام الفعل في صيغة المصدر المجرد (submit)."
    }
]

INELT_QUESTIONS_POOL = [
    {
        "q": "_____ had the ministerial invigilator distributed the exam papers than the listening section started.",
        "opts": ["No sooner", "Hardly", "Scarcely", "Barely"],
        "c": 0,
        "exp": "في اختبار INELT، التركيب المعتمد هو: <b>No sooner ... than</b>. بينما Hardly و Scarcely تأخذان (when)."
    },
    {
        "q": "[Error Identification]: Identify the incorrect word/phrase in the sentence:\n\n'The [impact] (A) of the novel findings [were] (B) recognized [immediately] (C) by the [scientific] (D) committee.'",
        "opts": ["(A) impact", "(B) were", "(C) immediately", "(D) scientific"],
        "c": 1,
        "exp": "الخطأ في (B) <b>were</b>. الفاعل هو المفرد (The impact)، لذا يجب أن يكون الفعل <b>was</b> (مطابقة الفاعل والفعل Subject-Verb Agreement)."
    },
    {
        "q": "The academic empirical study _____ at the annual symposium will be indexed in Scopus databases.",
        "opts": ["presented", "presenting", "was presented", "that presented"],
        "c": 0,
        "exp": "جملة موصولة مختصرة مبنية للمجهول <b>(Reduced Relative Clause)</b>: أصلها (which was presented) واختُصرت إلى <b>presented</b>."
    },
    {
        "q": "[Error Identification]: Identify the incorrect word/phrase in the sentence:\n\n'Despite [of] (A) the technical [difficulties] (B), the postgraduate students [submitted] (C) their papers [punctually] (D).'",
        "opts": ["(A) of", "(B) difficulties", "(C) submitted", "(D) punctually"],
        "c": 0,
        "exp": "الخطأ في (A) <b>of</b>. كلمة Despite لا تأخذ حرف الجر of أبداً (الصحيح: Despite the difficulties أو In spite of)."
    },
    {
        "q": "Before drawing definitive conclusions, academic scholars must _____ rigorous methodological research.",
        "opts": ["conduct", "make", "create", "construct"],
        "c": 0,
        "exp": "المتلازمة الأكاديمية الصحيحة (Academic Collocation) هي <b>conduct research</b> أو carry out research، واستخدام make يعتبر خطأ لغوياً شائعاً."
    },
    {
        "q": "[Error Identification]: Identify the incorrect word/phrase in the sentence:\n\n'Neither the [head of department] (A) nor the [professors] (B) [was] (C) present at the [ministerial] (D) meeting.'",
        "opts": ["(A) head of department", "(B) professors", "(C) was", "(D) present"],
        "c": 2,
        "exp": "الخطأ في (C) <b>was</b>. في قاعدة (Neither... nor) يتبع الفعل الفاعل الأقرب له، وبما أن professors جمع، يجب استخدام <b>were</b>."
    },
    {
        "q": "The doctoral program focuses on analyzing literature, mastering critical methodology, and _____ research papers.",
        "opts": ["publishing", "publish", "to publish", "published"],
        "c": 0,
        "exp": "قاعدة التوازي النحوي <b>(Parallelism)</b>: العطف على (analyzing, mastering) يتطلب استخدام صيغة الـ Gerund المماثلة: <b>publishing</b>."
    },
    {
        "q": "The doctoral dissertation provided _____ empirical evidence to corroborate the research hypothesis.",
        "opts": ["substantial", "superficial", "negligible", "trivial"],
        "c": 0,
        "exp": "مفردة <b>Substantial evidence</b> تعني أدلة جوهرية وقاطعة، وهي المفردة الأكاديمية الأنسب لسياق دعم الفرضيات العلمية."
    }
]

sim_competitive_sessions = {}
sim_inelt_sessions = {}

@courses_router.callback_query(F.data == "open_exam_simulators_hub")
async def handle_open_exam_simulators_hub(callback: CallbackQuery):
    """Joint hub for both the Competitive Exam and INELT National Exam simulators."""
    hub_text = (
        "🏛️ <b>منصة محاكاة الاختبارات الوطنية والتنافسية | National & Competitive Exam Hub</b> 🎯\n"
        "المشرف العام: <b>Lect. Mohammed Hussein</b> (مدرس جامعي متخصص في اللغة الإنجليزية والأدب العالمي)\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "أهلاً بك في المنصة التفاعلية المخصصة للمتقدمين للدراسات العليا (الماجستير والدكتوراه) واختبارات كفاءة اللغة في العراق:\n\n"
        "🎯 <b>1. محاكي الامتحان التنافسي (Competitive Exam Simulator):</b>\n"
        "• نماذج وزارية حقيقية لتخصص الأدب واللغة الإنجليزية.\n"
        "• يغطي: المسرح الشكسبيري، المدارس النقدية الحديثة، تيار الوعي، والقواعد المتقدمة (Inversion & Subjunctive).\n"
        "• شرح أكاديمي تحليلي لكل سؤال.\n\n"
        "🇮🇶 <b>2. محاكي اختبار INELT الوطني الموحد (INELT National Exam Simulator):</b>\n"
        "• مطابق للبيئة الحاسوبية للاختبار الوطني لوزارة التعليم العالي والبحث العلمي.\n"
        "• يغطي: التراكيب النحوية (Structure)، أسئلة اكتشاف الخطأ (Error Identification)، والمتلازمات الأكاديمية.\n"
        "• تقرير تشخيصي فوري بنهاية الاختبار لتحديد نسبة الجاهزية.\n\n"
        "👇 <b>اختر المسار الذي ترغب في محاكاته فوراً:</b>"
    )

    keyboard = [
        [InlineKeyboardButton(text="🎯 محاكي الامتحان التنافسي (ماجستير/دكتوراه)", callback_data="start_sim_competitive")],
        [InlineKeyboardButton(text="🇮🇶 محاكي اختبار INELT الوطني الموحد", callback_data="start_sim_inelt")],
        [
            InlineKeyboardButton(text="💡 استراتيجيات التنافسي", callback_data="tips_competitive"),
            InlineKeyboardButton(text="📊 أقسام وتفاصيل INELT", callback_data="structure_inelt")
        ],
        [InlineKeyboardButton(text="📲 حجز مقعد في الدورة التحضيرية المكثفة", url="https://t.me/Alzurfi1")],
        [InlineKeyboardButton(text="🔙 العودة لدليل الكورسات", callback_data="back_to_courses")]
    ]

    try:
        await callback.message.edit_text(hub_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(hub_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data == "course_competitive")
async def handle_course_competitive(callback: CallbackQuery):
    """Displays detailed overview for the Competitive Exam with simulator trigger."""
    text = (
        "🎯 <b>كورس ومحاكي الامتحان التنافسي للدراسات العليا</b>\n"
        "المشرف العام: <b>Lect. Mohammed Hussein</b>\n\n"
        "الدورة الأكاديمية الذهبية للمتقدمين للدراسات العليا (الماجستير والدكتوراه) في تخصص اللغة الإنجليزية والأدب بمختلف الجامعات العراقية.\n\n"
        "📌 <b>محاور الدورة والمحاكي التفاعلي:</b>\n"
        "• <b>محور الأدب والمسرح والشعر:</b> العصر الإليزابيثي، الرومانتيكية، والحداثة.\n"
        "• <b>محور النقد الأدبي والنظريات الحديثة:</b> البنيوية، التفكيكية، والنقد الجديد.\n"
        "• <b>محور القواعد الأكاديمية المتقدمة:</b> التراكيب المقلوبة (Inversion)، صيغ الـ Subjunctive، وتجنب الـ Dangling Modifiers.\n"
        "• <b>تحليل نماذج السنوات السابقة:</b> حل وتفكيك أسئلة الجامعات العراقية مع أسرار صياغة الأجوبة النموذجية.\n\n"
        "👇 <b>يمكنك خوض تجربة المحاكي التفاعلي الآن أو التواصل لحجز مقعدك:</b>"
    )
    keyboard = [
        [InlineKeyboardButton(text="🚀 بدء محاكي الامتحان التنافسي التفاعلي", callback_data="start_sim_competitive")],
        [InlineKeyboardButton(text="💡 استراتيجيات ونماذج أسئلة سابقة", callback_data="tips_competitive")],
        [InlineKeyboardButton(text="📲 حجز مقعد مع الأستاذ محمد حسين", url="https://t.me/Alzurfi1")],
        [InlineKeyboardButton(text="🔙 العودة لقائمة الكورسات", callback_data="back_to_courses")]
    ]
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data == "course_inelt")
async def handle_course_inelt(callback: CallbackQuery):
    """Displays detailed overview for the INELT National Exam with simulator trigger."""
    text = (
        "🇮🇶 <b>كورس ومحاكي الاختبار الوطني الموحد (INELT) | National Exam</b>\n"
        "المشرف العام: <b>Lect. Mohammed Hussein</b>\n\n"
        "الدورة التخصصية المكثفة لاجتياز اختبار اللغة الإنجليزية الوطني الموحد والمعتمد رسمياً من وزارة التعليم العالي والبحث العلمي كشرط ملزم للتقديم للدراسات العليا والترقيات العلمية.\n\n"
        "📌 <b>مميزات البرنامج التدريبي والمحاكي:</b>\n"
        "• <b>التدريب على بنية الامتحان الحاسوبي:</b> الاستماع، القواعد، والقراءة.\n"
        "• <b>إتقان نمط اكتشاف الخطأ (Error Identification):</b> الأسلوب الأكثر حيرة للطلاب في ورقة الاختبار.\n"
        "• <b>إدارة الوقت الذكية:</b> كيفية الإجابة على كل سؤال في أقل من 40 ثانية.\n"
        "• <b>نماذج امتحانية متجددة:</b> تحاكي الأسئلة الوزارية الرسمية بنسبة 100%.\n\n"
        "👇 <b>جرّب مستواك الآن في محاكي INELT الوطني أو تواصل للتسجيل:</b>"
    )
    keyboard = [
        [InlineKeyboardButton(text="🚀 خوض محاكي اختبار INELT الوطني الآن", callback_data="start_sim_inelt")],
        [InlineKeyboardButton(text="📊 دليل تقسيم أقسام ودرجات INELT", callback_data="structure_inelt")],
        [InlineKeyboardButton(text="📲 التسجيل وحجز مقعد في الدورة", url="https://t.me/Alzurfi1")],
        [InlineKeyboardButton(text="🔙 العودة لقائمة الكورسات", callback_data="back_to_courses")]
    ]
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

# --- محاكي الامتحان التنافسي (Competitive Exam Flow) ---
@courses_router.callback_query(F.data == "start_sim_competitive")
async def handle_start_sim_competitive(callback: CallbackQuery):
    user_id = callback.from_user.id
    selected_qs = random.sample(COMPETITIVE_QUESTIONS_POOL, min(5, len(COMPETITIVE_QUESTIONS_POOL)))
    sim_competitive_sessions[user_id] = {
        "questions": selected_qs,
        "current_idx": 0,
        "score": 0
    }

    first_q = selected_qs[0]
    keyboard = []
    for idx, opt in enumerate(first_q["opts"]):
        keyboard.append([
            InlineKeyboardButton(text=f"{chr(65+idx)}) {opt}", callback_data=f"sim_comp_ans_{idx}")
        ])

    card_text = (
        f"🎯 <b>محاكي الامتحان التنافسي للدراسات العليا | Competitive Exam</b>\n"
        f"المشرف العام: <b>Lect. Mohammed Hussein</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"❓ <b>السؤال 1 من {len(selected_qs)}:</b>\n"
        f"<b>{first_q['q']}</b>\n\n"
        f"<i>اختر الإجابة الأكاديمية الأدق أدناه:</i>"
    )
    try:
        await callback.message.edit_text(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data.startswith("sim_comp_ans_"))
async def handle_sim_comp_answer(callback: CallbackQuery):
    user_id = callback.from_user.id
    chosen_opt = int(callback.data.split("_")[-1])

    session = sim_competitive_sessions.get(user_id)
    if not session:
        await callback.answer("انتهت الجلسة، يرجى البدء من جديد.", show_alert=True)
        return

    questions = session["questions"]
    curr_idx = session["current_idx"]
    current_q = questions[curr_idx]

    is_correct = (chosen_opt == current_q["c"])
    if is_correct:
        session["score"] += 1

    feedback = "✅ <b>إجابة ممتازة وصحيحة وفق المعيار الأكاديمي!</b>" if is_correct else "❌ <b>إجابة غير صحيحة!</b>"
    explanation = f"{feedback}\n\n💡 <b>التحليل الأكاديمي:</b>\n{current_q['exp']}"

    session["current_idx"] += 1
    next_idx = session["current_idx"]

    if next_idx < len(questions):
        next_q = questions[next_idx]
        keyboard = []
        for idx, opt in enumerate(next_q["opts"]):
            keyboard.append([
                InlineKeyboardButton(text=f"{chr(65+idx)}) {opt}", callback_data=f"sim_comp_ans_{idx}")
            ])

        card_text = (
            f"{explanation}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"❓ <b>السؤال {next_idx + 1} من {len(questions)}:</b>\n"
            f"<b>{next_q['q']}</b>"
        )
        try:
            await callback.message.edit_text(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        except Exception:
            await callback.message.answer(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        await callback.answer()
    else:
        final_score = session["score"]
        total_q = len(questions)
        pct = round((final_score / total_q) * 100)

        if pct >= 80:
            evaluation = "🌟 <b>مستوى متقدم واستثنائي!</b> جاهزيتك ممتازة جداً لخوض الامتحان التنافسي الحقيقي والتفوق فيه."
        elif pct >= 60:
            evaluation = "👍 <b>أداء جيد جداً!</b> لديك أساس قوي ولكن تحتاج إلى تعزيز بعض النقاط النقدية والتراكيب الدقيقة."
        else:
            evaluation = "💪 <b>بداية طيبة وتحتاج لمراجعة مركزة!</b> نوصيك بالانضمام للدورة المكثفة لضبط محاور النقد والأدب."

        report_text = (
            f"{explanation}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 <b>التقرير التشخيصي للامتحان التنافسي</b> 🎓\n\n"
            f"📊 <b>نتيجتك في هذا النموذج:</b> {final_score} من {total_q} ({pct}%)\n"
            f"📌 <b>التقييم الأكاديمي:</b>\n{evaluation}\n\n"
            f"👨‍🏫 <b>توجيه الأستاذ محمد حسين:</b>\n"
            f"«الامتحان التنافسي لا يقيس الحفظ فقط، بل يقيس قدرتك على التحليل النقدي واستدعاء المصطلح المناسب في السياق السليم». "
            f"لضمان حجز مقعدك وتفوقك في المقبولين، يسعدنا انضمامك للدورة التحضيرية المكثفة.\n"
        )

        keyboard = [
            [InlineKeyboardButton(text="🔄 خوض نموذج عشوائي جديد", callback_data="start_sim_competitive")],
            [InlineKeyboardButton(text="📲 حجز مقعد في الدورة مع الأستاذ", url="https://t.me/Alzurfi1")],
            [InlineKeyboardButton(text="🇮🇶 الانتقال لمحاكي اختبار INELT", callback_data="start_sim_inelt")],
            [InlineKeyboardButton(text="🔙 العودة للمحاكي الرئيسي", callback_data="open_exam_simulators_hub")]
        ]

        try:
            await callback.message.edit_text(report_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        except Exception:
            await callback.message.answer(report_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        await callback.answer()
        sim_competitive_sessions.pop(user_id, None)

# --- محاكي اختبار INELT الوطني الموحد (INELT Exam Flow) ---
@courses_router.callback_query(F.data == "start_sim_inelt")
async def handle_start_sim_inelt(callback: CallbackQuery):
    user_id = callback.from_user.id
    selected_qs = random.sample(INELT_QUESTIONS_POOL, min(5, len(INELT_QUESTIONS_POOL)))
    sim_inelt_sessions[user_id] = {
        "questions": selected_qs,
        "current_idx": 0,
        "score": 0
    }

    first_q = selected_qs[0]
    keyboard = []
    for idx, opt in enumerate(first_q["opts"]):
        keyboard.append([
            InlineKeyboardButton(text=f"{opt}", callback_data=f"sim_inelt_ans_{idx}")
        ])

    card_text = (
        f"🇮🇶 <b>محاكي اختبار INELT الوطني الموحد | National Exam Mock</b>\n"
        f"المشرف العام: <b>Lect. Mohammed Hussein</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"❓ <b>السؤال 1 من {len(selected_qs)}:</b>\n"
        f"<b>{first_q['q']}</b>\n\n"
        f"<i>اختر الإجابة الصحيحة أو حدد الخطأ النحوي:</i>"
    )
    try:
        await callback.message.edit_text(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data.startswith("sim_inelt_ans_"))
async def handle_sim_inelt_answer(callback: CallbackQuery):
    user_id = callback.from_user.id
    chosen_opt = int(callback.data.split("_")[-1])

    session = sim_inelt_sessions.get(user_id)
    if not session:
        await callback.answer("انتهت الجلسة، يرجى البدء من جديد.", show_alert=True)
        return

    questions = session["questions"]
    curr_idx = session["current_idx"]
    current_q = questions[curr_idx]

    is_correct = (chosen_opt == current_q["c"])
    if is_correct:
        session["score"] += 1

    feedback = "✅ <b>إجابة صحيحة ومطابقة للنمط الوزاري!</b>" if is_correct else "❌ <b>إجابة غير صحيحة!</b>"
    explanation = f"{feedback}\n\n💡 <b>التحليل والقاعدة النحوية:</b>\n{current_q['exp']}"

    session["current_idx"] += 1
    next_idx = session["current_idx"]

    if next_idx < len(questions):
        next_q = questions[next_idx]
        keyboard = []
        for idx, opt in enumerate(next_q["opts"]):
            keyboard.append([
                InlineKeyboardButton(text=f"{opt}", callback_data=f"sim_inelt_ans_{idx}")
            ])

        card_text = (
            f"{explanation}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"❓ <b>السؤال {next_idx + 1} من {len(questions)}:</b>\n"
            f"<b>{next_q['q']}</b>"
        )
        try:
            await callback.message.edit_text(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        except Exception:
            await callback.message.answer(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        await callback.answer()
    else:
        final_score = session["score"]
        total_q = len(questions)
        pct = round((final_score / total_q) * 100)

        if pct >= 80:
            evaluation = "🎉 <b>جاهزية فائقة لاجتياز INELT!</b> تحكمك في تراكيب Structure واكتشاف الأخطاء ممتاز جداً."
        elif pct >= 60:
            evaluation = "⚖️ <b>مستوى مؤهل للنجاح!</b> ينصح بزيادة التدريب على أنماط Error Identification لرفع درجتك إلى الامتياز."
        else:
            evaluation = "⚠️ <b>بحاجة إلى خطة تدريبية مكثفة!</b> اختبار INELT يعتمد على السرعة واكتشاف الفخاخ النحوية، وننصحك ببدء التدريب فوراً."

        report_text = (
            f"{explanation}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🇮🇶 <b>تقرير محاكي اختبار INELT الوطني الموحد</b> 🎓\n\n"
            f"📊 <b>الدرجة المحققة:</b> {final_score} من {total_q} ({pct}%)\n"
            f"📌 <b>التقييم الوزاري:</b>\n{evaluation}\n\n"
            f"📝 <b>ملاحظة هامة للمتقدمين:</b>\n"
            f"درجة النجاح المشروطة للاختبار الوطني تختلف حسب التخصص (إنساني أو علمي)، واكتساب استراتيجيات الحل السريع يضمن لك تحقيق الدرجة المطلوبة من المحاولة الأولى بإذن الله.\n"
        )

        keyboard = [
            [InlineKeyboardButton(text="🔄 إعادة المحاكي بنموذج جديد", callback_data="start_sim_inelt")],
            [InlineKeyboardButton(text="📲 التسجيل في دورة INELT مع الأستاذ", url="https://t.me/Alzurfi1")],
            [InlineKeyboardButton(text="🎯 الانتقال لمحاكي الامتحان التنافسي", callback_data="start_sim_competitive")],
            [InlineKeyboardButton(text="🔙 العودة للمحاكي الرئيسي", callback_data="open_exam_simulators_hub")]
        ]

        try:
            await callback.message.edit_text(report_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        except Exception:
            await callback.message.answer(report_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        await callback.answer()
        sim_inelt_sessions.pop(user_id, None)

@courses_router.callback_query(F.data == "tips_competitive")
async def handle_tips_competitive(callback: CallbackQuery):
    """Provides high-value strategies for the Competitive Exam."""
    tips_text = (
        "💡 <b>أهم استراتيجيات التفوق في الامتحان التنافسي للدراسات العليا</b> 🎓\n"
        "إعداد وتوجيه: <b>Lect. Mohammed Hussein</b>\n\n"
        "1. <b>فهم السؤال النقدي بعمق:</b> لا تتسرع في كتابة كل ما تعرفه عن الكاتب؛ ركز بدقة على المفهوم المطلوب (مثل: النزعة التفكيكية، الرمزية، أو البناء الدرامي).\n\n"
        "2. <b>الدقة في المصطلحات (Terminology):</b> استخدام المصطلح النقدي الدقيق (مثل *Catharsis*, *Hamartia*, *Objective Correlative*) يمنح إجابتك وزناً أكاديمياً فورياً أمام لجان التصحيح.\n\n"
        "3. <b>تجنب الأخطاء الأسلوبية الشائعة:</b> ابتعد عن الجمل الطويلة غير المترابطة (Run-on sentences)، واحرص على تجنب الـ Dangling Modifiers وضبط التوازي (Parallelism).\n\n"
        "4. <b>تنظيم الوقت:</b> خصص الدقائق الأولى لتخطيط الإجابة ووضع النقاط الرئيسية قبل البدء بالكتابة المفصلة.\n\n"
        "🌟 <i>نقدم في دورتنا المكثفة تدريباً تفاعلياً مباشراً وتصحيحاً أسبوعياً للنماذج الوزارية.</i>"
    )
    keyboard = [
        [InlineKeyboardButton(text="🚀 بدء محاكي الامتحان التنافسي الآن", callback_data="start_sim_competitive")],
        [InlineKeyboardButton(text="💬 التواصل مع الأستاذ للتسجيل", url="https://t.me/Alzurfi1")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="course_competitive")]
    ]
    try:
        await callback.message.edit_text(tips_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(tips_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data == "structure_inelt")
async def handle_structure_inelt(callback: CallbackQuery):
    """Provides breakdown of INELT exam sections and time allocation."""
    struct_text = (
        "📊 <b>دليل أقسام واختبار اللغة الإنجليزية الوطني الموحد (INELT)</b> 🇮🇶\n\n"
        "يتكون الاختبار الوطني المحوسب من ثلاثة أقسام رئيسية تركز على قياس الكفاءة الأكاديمية:\n\n"
        "🎧 <b>1. قسم الاستماع (Listening Comprehension):</b>\n"
        "• محادثات أكاديمية وحوارات قصيرة.\n"
        "• يركز على استخلاص الفكرة الرئيسية (Main Idea) والتفاصيل الدقيقة واللكنة المعتمدة.\n\n"
        "📐 <b>2. قسم القواعد والتراكيب (Structure & Written Expression):</b>\n"
        "• <b>الجزء الأول:</b> إكمال الجمل المعقدة وصيغ الشرط والروابط.\n"
        "• <b>الجزء الثاني:</b> اكتشاف الخطأ (Error Identification) في الجمل الأكاديمية، وهو القسم الذي يحتاج أكبر قدر من الممارسة.\n\n"
        "📖 <b>3. قسم القراءة والمفردات الأكاديمية (Reading & Vocabulary):</b>\n"
        "• نصوص علمية وإنسانية مع أسئلة استنتاجية ومعاني الكلمات في السياق.\n\n"
        "⏳ <b>إدارة الوقت:</b> الاختبار سريع ويحتاج إلى سرعة بديهة واستبعاد الخيارات الخاطئة فوراً."
    )
    keyboard = [
        [InlineKeyboardButton(text="🚀 خوض محاكي INELT الوطني الآن", callback_data="start_sim_inelt")],
        [InlineKeyboardButton(text="💬 حجز مقعد في الدورة التحضيرية", url="https://t.me/Alzurfi1")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="course_inelt")]
    ]
    try:
        await callback.message.edit_text(struct_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(struct_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

# ---------------------------------------------------------------------------
# 5. Browse Lessons from Database & Lesson Reader
# ---------------------------------------------------------------------------
@courses_router.callback_query(F.data.in_(["browse_available_lessons", "back_to_catalog"]))
async def handle_browse_lessons_from_db(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        query = select(Course).where(Course.is_published == True)
        result = await session.execute(query)
        courses = result.scalars().all()

    if not courses:
        text = (
            "📚 <b>الدروس الأكاديمية المتاحة | Lessons</b>\n\n"
            "يتم حالياً رفع المناهج والدروس الأسبوعية بإشراف الأستاذ.\n"
            "تابع القناة الرسمية أو تواصل مع الإدارة لمعرفة مواعيد فتح التسجيل."
        )
        keyboard = [
            [InlineKeyboardButton(text="📢 القناة الرسمية", url="https://t.me/FluenceEnglish")],
            [InlineKeyboardButton(text="🔙 العودة للكورسات", callback_data="back_to_courses")]
        ]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        await callback.answer()
        return

    keyboard = []
    for c in courses:
        keyboard.append([InlineKeyboardButton(text=f"📖 {c.title}", callback_data=f"open_course_{c.id}")])
    keyboard.append([InlineKeyboardButton(text="🔙 العودة للكورسات", callback_data="back_to_courses")])

    await callback.message.edit_text(
        "📚 <b>اختر الكورس لعرض قائمة المحاضرات والدروس:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()

@courses_router.callback_query(F.data.startswith("open_course_"))
async def handle_open_single_course(callback: CallbackQuery):
    course_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        c_query = select(Course).where(Course.id == course_id)
        c_res = await session.execute(c_query)
        course = c_res.scalar_one_or_none()

        l_query = select(Lesson).where(Lesson.course_id == course_id, Lesson.is_published == True).order_by(Lesson.order_index)
        l_res = await session.execute(l_query)
        lessons = l_res.scalars().all()

    if not course:
        await callback.answer("الكورس غير متاح حالياً.", show_alert=True)
        return

    text = (
        f"📖 <b>{course.title}</b>\n\n"
        f"{course.description or 'منهاج أكاديمي تخصصي بإشراف Lect. Mohammed Hussein'}\n\n"
        f"📑 <b>قائمة الدروس والمحاضرات:</b>"
    )

    keyboard = []
    for les in lessons:
        keyboard.append([InlineKeyboardButton(text=f"▶️ الدرس {les.order_index}: {les.title}", callback_data=f"read_lesson_{les.id}")])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="browse_available_lessons")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@courses_router.callback_query(F.data.startswith("read_lesson_"))
async def handle_read_lesson_content(callback: CallbackQuery):
    lesson_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        query = select(Lesson).where(Lesson.id == lesson_id)
        result = await session.execute(query)
        lesson = result.scalar_one_or_none()

    if not lesson:
        await callback.answer("الدرس غير متوفر.", show_alert=True)
        return

    body = lesson.content_text or "المحتوى النصي قيد التحديث."
    card_text = (
        f"📘 <b>{lesson.title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"{body}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👇 يمكنك خوض اختبار هذا الدرس فوراً لتقييم فهمك:"
    )

    keyboard = [
        [InlineKeyboardButton(text="🧠 بدء اختبار هذا الدرس", callback_data=f"start_quiz_{lesson.id}")],
        [InlineKeyboardButton(text="🔙 العودة لقائمة الدروس", callback_data=f"open_course_{lesson.course_id}")]
    ]

    await callback.message.edit_text(card_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()
