from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Returns the bilingual main menu keyboard:
    Row 1: [ 📚 الدورات التدريبية | Courses ] [ 📝 اختبار تحديد المستوى | Placement Test ]
    Row 2: [ 🎯 تحدي اليوم ] [ 🎯 الاختبارات اليومية | Quizzes ]
    Row 3: [ 🤖 المساعد اللغوي ] [ 📝 مصحح الكتابة الأكاديمية ]
    Row 4: [ 📁 الملفات والمواد | Study Files & Materials ]
    Row 5: [ ✨ عن الأكاديمية | About Fluence ] [ 💬 الدعم والتواصل | Help & Support ]
    """
    keyboard = [
        [
            KeyboardButton(text="📚 الدورات التدريبية | Courses"),
            KeyboardButton(text="📝 اختبار تحديد المستوى | Placement Test")
        ],
        [
            KeyboardButton(text="🎯 تحدي اليوم"),
            KeyboardButton(text="🎯 الاختبارات اليومية | Quizzes")
        ],
        [
            KeyboardButton(text="🤖 المساعد اللغوي"),
            KeyboardButton(text="📝 مصحح الكتابة الأكاديمية")
        ],
        [
            KeyboardButton(text="📁 الملفات والمواد | Study Files & Materials")
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

def get_academic_writing_keyboard() -> ReplyKeyboardMarkup:
    """Returns the keyboard while in Academic Writing Review mode."""
    keyboard = [
        [
            KeyboardButton(text="🔙 العودة للقائمة الرئيسية")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="أرسل مقالك أو نصك الأكاديمي للتدقيق..."
    )

def get_daily_challenge_keyboard() -> ReplyKeyboardMarkup:
    """Returns the keyboard while answering the Daily Challenge."""
    keyboard = [
        [
            KeyboardButton(text="🎯 سؤال آخر | New Question"),
            KeyboardButton(text="🔙 العودة للقائمة الرئيسية")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="اكتب إجابتك هنا (مثلاً: A أو الإجابة المباشرة)..."
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
    - 📝 اختبار تحديد المستوى الرسمي | Placement Test
    - 🏛️ كورسات اللغة الأكاديمية | Academic English
    - 🗣️ كورسات اللغة العامة | General English
    - 🎯 كورس الامتحان التنافسي | Competitive Exam
    - 🇮🇶 كورس الاختبار الوطني (INELT) | National Exam
    - 🔙 العودة للقائمة الرئيسية | Main Menu
    """
    keyboard = [
        [InlineKeyboardButton(text="📝 اختبار تحديد المستوى الرسمي (مع الشهادة 🎓)", callback_data="start_placement_test")],
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
    - 🎯 اختبار تحديد المستوى التشخيصي
    - 🌱 المستوى المبتدئ | Beginner (A1)
    - 📘 المستوى الأساسي | Elementary (A2)
    - 📙 المستوى قبل المتوسط | Pre-Intermediate (B1)
    - 📕 المستوى المتوسط | Intermediate & Upper (B2)
    - 🎓 المستوى المتقدم | Advanced (C1)
    - 🏆 مستوى الإتقان التام | Proficiency (C2)
    - 🔙 رجوع | Back
    """
    keyboard = [
        [InlineKeyboardButton(text="🎯 لست متأكداً من مستواك؟ ابدأ الاختبار التشخيصي 📝", callback_data="start_placement_test")],
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
    keyboard = [
        [InlineKeyboardButton(text="✍️ الكتابة الأكاديمية والبحوث | Academic Writing & Research", callback_data="acad_writing")],
        [InlineKeyboardButton(text="🎤 مهارات العرض والإلقاء | Academic Presentations", callback_data="acad_presentations")],
        [InlineKeyboardButton(text="🗣️ النطق والتجويد اللفظي | Pronunciation & Phonetics", callback_data="acad_phonetics")],
        [InlineKeyboardButton(text="🔙 رجوع | Back", callback_data="back_to_courses")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_exam_details_keyboard(exam_type: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="📋 متطلبات وتفاصيل الدورة", callback_data=f"exam_details_{exam_type}")],
        [InlineKeyboardButton(text="📝 حجز مقعد في الدورة", callback_data=f"enroll_{exam_type}")],
        [InlineKeyboardButton(text="🔙 رجوع | Back", callback_data="back_to_courses")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_sub_level_keyboard(parent_category: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="📝 التسجيل في هذا المستوى", callback_data=f"enroll_{parent_category}")],
        [InlineKeyboardButton(text="🔙 رجوع | Back", callback_data=parent_category)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_library_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="📘 ملازم ومناهج اللغة العامة", callback_data="lib_general")],
        [InlineKeyboardButton(text="🏛️ بحوث وأدلة الدراسات العليا", callback_data="lib_postgrad")],
        [InlineKeyboardButton(text="🎯 نماذج الامتحان التنافسي و INELT", callback_data="lib_exams")],
        [InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="back_to_main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_library_back_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🔙 العودة للمكتبة", callback_data="open_library")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
