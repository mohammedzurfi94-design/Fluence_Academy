from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Returns the bilingual main menu keyboard:
    Row 1: [ 📚 الدورات التدريبية | Courses ] [ 📝 اختبار المستوى | Placement Test ]
    Row 2: [ 🎯 الاختبارات اليومية | Quizzes ] [ 📁 الملفات والمواد | Study Files & Materials ]
    Row 3: [ 🤖 المساعد اللغوي (AI Tutor) ]
    Row 4: [ ✨ عن الأكاديمية | About Fluence ] [ 💬 الدعم والتواصل | Help & Support ]
    """
    keyboard = [
        [
            KeyboardButton(text="📚 الدورات التدريبية | Courses"),
            KeyboardButton(text="📝 اختبار المستوى | Placement Test")
        ],
        [
            KeyboardButton(text="🎯 الاختبارات اليومية | Quizzes"),
            KeyboardButton(text="📁 الملفات والمواد | Study Files & Materials")
        ],
        [
            KeyboardButton(text="🤖 المساعد اللغوي (AI Tutor)")
        ],
        [
            KeyboardButton(text="✨ عن الأكاديمية | About Fluence"),
            KeyboardButton(text="💬 الدعم والتواصل | Help & Support")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="اختر من القائمة أدناه | Choose an option..."
    )

def get_ai_chat_keyboard() -> ReplyKeyboardMarkup:
    """Returns the chat keyboard while conversing with the AI Tutor."""
    keyboard = [
        [
            KeyboardButton(text="🔙 إنهاء المحادثة")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="اكتب رسالتك بالإنجليزية | Type in English..."
    )

def get_channel_join_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    """Returns an inline button asking student to join the required channel."""
    keyboard = [
        [InlineKeyboardButton(text="📢 انضم إلى القناة الرسمية", url=channel_url)],
        [InlineKeyboardButton(text="✅ تحقق من الاشتراك", callback_data="check_channel_joined")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_courses_catalog_keyboard() -> InlineKeyboardMarkup:
    """
    Main Courses Categories Keyboard:
    - 🏛️ كورسات اللغة الأكاديمية | Academic English
    - 🗣️ كورسات اللغة العامة | General English
    - 🎯 كورس الامتحان التنافسي | Competitive Exam
    - 🇮🇶 كورس الاختبار الوطني (INELT) | National Exam
    - 🔙 العودة للقائمة الرئيسية | Main Menu
    """
    keyboard = [
        [InlineKeyboardButton(text="🏛️ كورسات اللغة الأكاديمية | Academic English", callback_data="cat_academic")],
        [InlineKeyboardButton(text="🗣️ كورسات اللغة العامة | General English", callback_data="cat_general")],
        [InlineKeyboardButton(text="🎯 كورس الامتحان التنافسي | Competitive Exam", callback_data="course_competitive")],
        [InlineKeyboardButton(text="🇮🇶 كورس الاختبار الوطني (INELT) | National Exam", callback_data="course_inelt")],
        [InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية | Main Menu", callback_data="back_to_main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_general_english_keyboard() -> InlineKeyboardMarkup:
    """
    General English levels:
    - 🌱 المستوى المبتدئ | Beginner (A1)
    - 📘 المستوى الأساسي | Elementary (A2)
    - 📙 المستوى قبل المتوسط | Pre-Intermediate (B1)
    - 📕 المستوى المتوسط | Intermediate & Upper (B2)
    - 🎓 المستوى المتقدم | Advanced (C1)
    - 🏆 مستوى الإتقان التام | Proficiency (C2)
    - 🔙 رجوع | Back
    """
    keyboard = [
        [InlineKeyboardButton(text="🌱 المستوى المبتدئ | Beginner (A1)", callback_data="level_a1")],
        [InlineKeyboardButton(text="📘 المستوى الأساسي | Elementary (A2)", callback_data="level_a2")],
        [InlineKeyboardButton(text="📙 المستوى قبل المتوسط | Pre-Intermediate (B1)", callback_data="level_b1")],
        [InlineKeyboardButton(text="📕 المستوى المتوسط | Intermediate & Upper (B2)", callback_data="level_b2")],
        [InlineKeyboardButton(text="🎓 المستوى المتقدم | Advanced (C1)", callback_data="level_c1")],
        [InlineKeyboardButton(text="🏆 مستوى الإتقان التام | Proficiency (C2)", callback_data="level_c2")],
        [InlineKeyboardButton(text="🔙 رجوع | Back", callback_data="back_to_courses")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_academic_english_keyboard() -> InlineKeyboardMarkup:
    """
    Academic English tracks:
    - ✍️ الكتابة الأكاديمية والبحوث | Academic Writing & Research
    - 🎤 مهارات العرض والإلقاء | Academic Presentations
    - 🗣️ النطق والتجويد اللفظي | Pronunciation & Phonetics
    - 🔙 رجوع | Back
    """
    keyboard = [
        [InlineKeyboardButton(text="✍️ الكتابة الأكاديمية والبحوث | Academic Writing & Research", callback_data="acad_writing")],
        [InlineKeyboardButton(text="🎤 مهارات العرض والإلقاء | Academic Presentations", callback_data="acad_presentations")],
        [InlineKeyboardButton(text="🗣️ النطق والتجويد اللفظي | Pronunciation & Phonetics", callback_data="acad_phonetics")],
        [InlineKeyboardButton(text="🔙 رجوع | Back", callback_data="back_to_courses")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_exam_details_keyboard(contact_url: str = "https://t.me/Alzurfi1", button_text: str = "📲 للتسجيل والتواصل مع الإدارة | Contact & Register") -> InlineKeyboardMarkup:
    """
    Direct registration and contact keyboard for Competitive Exam and INELT.
    """
    keyboard = [
        [InlineKeyboardButton(text=button_text, url=contact_url)],
        [InlineKeyboardButton(text="🔙 رجوع | Back", callback_data="back_to_courses")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_sub_level_keyboard(parent_back: str, browse_callback: str = "browse_available_lessons") -> InlineKeyboardMarkup:
    """Returns registration button and back button to parent category and main catalog."""
    keyboard = [
        [InlineKeyboardButton(text="💬 التواصل مع الأستاذ للتسجيل", url="https://t.me/Fluenceacademy")],
        [InlineKeyboardButton(text="📚 تصفح الدروس المتاحة | Available Lessons", callback_data=browse_callback)],
        [InlineKeyboardButton(text="🔙 رجوع | Back", callback_data=parent_back)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_library_keyboard() -> InlineKeyboardMarkup:
    """
    Library Categories Keyboard:
    - 🎁 الملفات الخاصة بالأستاذ | Teacher's Exclusive Files
    - 📝 ملخصات القواعد | Grammar Summaries
    - 🗣 أدلة التلفظ | Phonetics Guides
    - 🎯 نماذج الامتحانات | Exam Past Papers
    - 🔙 العودة للقائمة الرئيسية | Main Menu
    """
    keyboard = [
        [InlineKeyboardButton(text="🎁 الملفات الخاصة بالأستاذ | Teacher's Exclusive Files", callback_data="files_teacher")],
        [InlineKeyboardButton(text="📝 ملخصات القواعد | Grammar Summaries", callback_data="files_grammar")],
        [InlineKeyboardButton(text="🗣 أدلة التلفظ | Phonetics Guides", callback_data="files_phonetics")],
        [InlineKeyboardButton(text="🎯 نماذج الامتحانات | Exam Past Papers", callback_data="files_exams")],
        [InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية | Main Menu", callback_data="back_to_main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_library_back_keyboard() -> InlineKeyboardMarkup:
    """Returns back button to the digital library menu."""
    keyboard = [
        [InlineKeyboardButton(text="🔙 رجوع | Back", callback_data="back_to_library")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
