from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Main persistent navigation keyboard for Fluence Academy."""
    keyboard = [
        [
            KeyboardButton(text="📚 الدورات الأكاديمية | Courses"),
            KeyboardButton(text="🎯 الاختبارات اليومية | Quizzes")
        ],
        [
            KeyboardButton(text="🎯 تحدي اليوم"),
            KeyboardButton(text="🤖 المساعد اللغوي (AI Tutor)")
        ],
        [
            KeyboardButton(text="📝 مصحح الكتابة الأكاديمية")
        ],
        [
            KeyboardButton(text="📊 درجاتي وإحصائياتي | My Stats"),
            KeyboardButton(text="📖 المكتبة التعليمية | Library")
        ],
        [
            KeyboardButton(text="ℹ️ عن الأكاديمية | About Us"),
            KeyboardButton(text="💬 الدعم الفني والاستفسارات | Support")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="اختر من القائمة الرئيسية للأكاديمية..."
    )

def get_ai_chat_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard active during interactive English Tutor chat mode."""
    keyboard = [
        [KeyboardButton(text="🔙 إنهاء المحادثة والعودة للقائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="تحدث بالإنجليزية، اسأل عن قاعدة، أو أرسل فويس نوت 🎙️..."
    )

def get_academic_writing_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for Academic Writing Reviewer mode."""
    keyboard = [
        [KeyboardButton(text="🔙 العودة للقائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="أرسل مقالك أو نصك الأكاديمي للتدقيق والتقييم..."
    )

def get_daily_challenge_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for Daily Challenge mode."""
    keyboard = [
        [KeyboardButton(text="🎯 سؤال آخر | New Question")],
        [KeyboardButton(text="🔙 العودة للقائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="اكتب إجابتك هنا وسيقوم الأستاذ بتقييمها..."
    )

def get_channel_join_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    """Inline keyboard requiring channel subscription."""
    keyboard = [
        [InlineKeyboardButton(text="📢 انضم إلى قناة الأكاديمية", url=channel_url)],
        [InlineKeyboardButton(text="✅ تحقّق من اشتراكي الآن", callback_data="check_subscription")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_courses_catalog_keyboard() -> InlineKeyboardMarkup:
    """Top-level courses categories."""
    keyboard = [
        [InlineKeyboardButton(text="🎓 البرنامج الأكاديمي الجامعي (4 سنوات)", callback_data="cat_academic")],
        [InlineKeyboardButton(text="🗣️ اللغة الإنجليزية العامة والمهارات", callback_data="cat_general")],
        [InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_academic_english_keyboard() -> InlineKeyboardMarkup:
    """University 4-year curriculum keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(text="السنة الأولى | First Year", callback_data="acad_year_1"),
            InlineKeyboardButton(text="السنة الثانية | Second Year", callback_data="acad_year_2")
        ],
        [
            InlineKeyboardButton(text="السنة الثالثة | Third Year", callback_data="acad_year_3"),
            InlineKeyboardButton(text="السنة الرابعة | Fourth Year", callback_data="acad_year_4")
        ],
        [InlineKeyboardButton(text="🔙 رجوع للأقسام", callback_data="courses_catalog")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_general_english_keyboard() -> InlineKeyboardMarkup:
    """General English CEFR tracks."""
    keyboard = [
        [
            InlineKeyboardButton(text="A1 - المبتدئ", callback_data="gen_a1"),
            InlineKeyboardButton(text="A2 - الأساسي", callback_data="gen_a2")
        ],
        [
            InlineKeyboardButton(text="B1 - المتوسط", callback_data="gen_b1"),
            InlineKeyboardButton(text="B2 - فوق المتوسط", callback_data="gen_b2")
        ],
        [
            InlineKeyboardButton(text="C1 - المتقدم", callback_data="gen_c1"),
            InlineKeyboardButton(text="C2 - الإتقان والطلاقة", callback_data="gen_c2")
        ],
        [InlineKeyboardButton(text="🔙 رجوع للأقسام", callback_data="courses_catalog")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_sub_level_keyboard(category_code: str) -> InlineKeyboardMarkup:
    """Interactive sub-level keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(text="📖 تفاصيل المستوى", callback_data=f"info_{category_code}"),
            InlineKeyboardButton(text="📝 اختبار تحديد المستوى", callback_data=f"placement_{category_code}")
        ],
        [
            InlineKeyboardButton(text="📚 المواد والمحاضرات", callback_data=f"materials_{category_code}"),
            InlineKeyboardButton(text="💬 حلقة نقاش الطلاب", callback_data=f"discussion_{category_code}")
        ],
        [InlineKeyboardButton(text="🔙 العودة لقائمة المستويات", callback_data="cat_general")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_exam_details_keyboard(exam_code: str) -> InlineKeyboardMarkup:
    """Exam preparation actions."""
    keyboard = [
        [
            InlineKeyboardButton(text="📋 هيكل ومحتوى الاختبار", callback_data=f"struct_{exam_code}"),
            InlineKeyboardButton(text="🎯 خطة دراسية مكثفة", callback_data=f"plan_{exam_code}")
        ],
        [
            InlineKeyboardButton(text="🧪 اختبار تجريبي كامل (Mock)", callback_data=f"mock_{exam_code}"),
            InlineKeyboardButton(text="💡 استراتيجيات تحقيق الدرجة", callback_data=f"tips_{exam_code}")
        ],
        [InlineKeyboardButton(text="🔙 العودة لقائمة الاختبارات", callback_data="courses_catalog")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_library_keyboard() -> InlineKeyboardMarkup:
    """Educational Library resources."""
    keyboard = [
        [InlineKeyboardButton(text="📚 ملخصات قواعد اللغة (PDF)", callback_data="lib_grammar_pdf")],
        [InlineKeyboardButton(text="🎧 نصوص استماع وتمارين صوتية", callback_data="lib_audio_transcripts")],
        [InlineKeyboardButton(text="📝 بنك نماذج وأسئلة الامتحانات", callback_data="lib_exam_bank")],
        [InlineKeyboardButton(text="📖 قوائم المفردات الأكاديمية (AWL)", callback_data="lib_vocab_lists")],
        [InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_library_back_keyboard() -> InlineKeyboardMarkup:
    """Back button for library sections."""
    keyboard = [
        [InlineKeyboardButton(text="🔙 العودة للمكتبة التعليمية", callback_data="open_library")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
