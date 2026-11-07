import html
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from datetime import datetime

from app.database.connection import AsyncSessionLocal
from app.database.models import User, Subscription
from app.bot.keyboards.main_menu import get_main_reply_keyboard, get_channel_join_keyboard
from app.core.config import settings
from app.services.channel_service import check_user_channel_membership

start_router = Router(name="start_router")

def get_start_hub_inline_keyboard() -> InlineKeyboardMarkup:
    """Returns interactive hub buttons with direct clickable divisions for the /start welcome card."""
    keyboard = [
        [
            InlineKeyboardButton(text="📚 دليل وتفاصيل الكورسات | Courses", callback_data="back_to_courses"),
            InlineKeyboardButton(text="📝 اختبار تحديد المستوى المتجدد", callback_data="start_placement_test")
        ],
        [
            InlineKeyboardButton(text="💡 معلومة اليوم واختبارها (🎙️)", callback_data="open_daily_info"),
            InlineKeyboardButton(text="🎯 تحدي اليوم الذكي (AI Challenge)", callback_data="open_daily_challenge")
        ],
        [
            InlineKeyboardButton(text="🤖 المساعد اللغوي (AI Tutor)", callback_data="start_ai_tutor_chat"),
            InlineKeyboardButton(text="✍️ مصحح الكتابة الأكاديمية", callback_data="start_academic_reviewer_chat")
        ],
        [
            InlineKeyboardButton(text="📁 المكتبة التعليمية والملفات", callback_data="open_library"),
            InlineKeyboardButton(text="💬 الدعم والتواصل مع الإدارة", callback_data="open_support_dialog")
        ],
        [
            InlineKeyboardButton(text="✨ نبذة ورؤية الأكاديمية | About", callback_data="open_about_fluence")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_welcome_card_text(student_name: str) -> str:
    """Generates the rich, prestigious academy welcome and divisions overview card."""
    clean_name = html.escape(student_name or "Student")
    return (
        f"🌟 <b>مرحباً بك في أكاديمية Fluence للغة الإنجليزية يا {clean_name}!</b> 🎓\n"
        f"المشرف العام: <b>Lect. Mohammed Hussein</b> (مدرس جامعي متخصص في اللغة الإنجليزية والأدب العالمي).\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏛️ <b>الأقسام والخدمات الأكاديمية المتاحة في المنصة:</b>\n\n"
        f"📚 <b>1. دليل الكورسات والدورات الأكاديمية المعتمدة:</b>\n"
        f"• 🗣️ <b>كورسات اللغة العامة (General English):</b> تشمل المستويات (A1 المبتدئ، A2 الأساسي، B1 المتوسط، B2 فوق المتوسط) مع مناهج تفاعلية حديثة.\n"
        f"• 🏛️ <b>كورسات اللغة الأكاديمية:</b> مخصصة للدراسات العليا والبحث العلمي وصياغة الأطروحات.\n"
        f"• 🎯 <b>الكورس المكثف للامتحان التنافسي:</b> للمتقدمين للماجستير والدكتوراه.\n"
        f"• 🇮🇶 <b>كورس الاختبار الوطني الموحد (INELT):</b> تدريب شامل للنجاح في الاختبار الوطني.\n\n"
        f"📝 <b>2. اختبار تحديد المستوى الذكي (متجدد آلياً):</b>\n"
        f"• 20 سؤالاً تشخيصياً دقيقاً متدرج الصعوبة من A1 إلى C2.\n"
        f"• 🔄 <b>نماذج متجددة:</b> لا تتكرر نفس الأسئلة إذا أعدت الاختبار، لضمان قياس مستواك الحقيقي.\n"
        f"• حفظ النتيجة الرسمية تلقائياً في قاعدة بيانات الأكاديمية على Notion.\n\n"
        f"💡 <b>3. معلومة اليوم واختبارها التفاعلي (🎙️):</b>\n"
        f"• محتوى تعليمي يومي يركز على القواعد، الأفعال المركبة (Phrasal Verbs)، والمصطلحات الأكاديمية.\n"
        f"• بصمة صوتية مرفقة باللكنة البريطانية المعتمدة (British Accent).\n"
        f"• زر اختبار فهم فوري لقياس مدى استيعابك للمعلومة.\n\n"
        f"🎯 <b>4. تحدي اليوم الذكي (Daily AI Challenge):</b>\n"
        f"• أسئلة لغوية تفاعلية فورية ومباشرة مدعومة بذكاء Groq الفائق.\n\n"
        f"🤖 <b>5. المساعد اللغوي ومصحح الكتابة (AI Tutor):</b>\n"
        f"• محادثة وممارسة نصية وصوتية (Voice Notes) مع رد صوتي بريطاني فوري.\n"
        f"• تدقيق المقالات والأبحاث وتحليل النصوص الأدبية بواسطة بروفيسور أكاديمي ذكي.\n\n"
        f"📁 <b>6. المكتبة الرقمية والملفات:</b> ملازم، أدلة بحوث التخرج، ودليل مناقشة الأطروحة.\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👇 <b>اختر من الأزرار التفاعلية أدناه لبدء رحلتك التعليمية فوراً:</b>"
    )

@start_router.message(CommandStart())
async def handle_start(message: Message):
    """Handles the /start command and automatically registers new students."""
    tg_user = message.from_user
    if not tg_user:
        return

    # Direct Force Subscription check for channel membership
    bot = message.bot
    if bot:
        is_member, _ = await check_user_channel_membership(bot, tg_user.id)
        if not is_member:
            channel = settings.REQUIRED_TELEGRAM_CHANNEL or "@FluenceEnglish"
            clean_channel = channel.replace("@", "")
            channel_url = f"https://t.me/{clean_channel}"
            prompt_text = (
                f"⚠️ <b>عذراً، يجب عليك الاشتراك في القناة أولاً!</b>\n\n"
                f"للاستفادة من محتوى <b>Fluence Academy</b> والوصول إلى كافة الكورسات والدروس والاختبارات، "
                f"يرجى الانضمام إلى قناتنا الرسمية:\n"
                f"👉 <b>{channel}</b>\n\n"
                f"اضغط على الزر أدناه للانضمام، ثم اضغط على <b>«تحقق من الاشتراك ✅»</b> للبدء فوراً! 👇"
            )
            await message.answer(
                prompt_text,
                reply_markup=get_channel_join_keyboard(channel_url),
                parse_mode="HTML"
            )
            return

    telegram_id = tg_user.id
    full_name = tg_user.full_name or "Student"
    username = tg_user.username

    async with AsyncSessionLocal() as session:
        try:
            # Check if student is already in the database
            query = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                # Auto-register new student
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    full_name=full_name,
                    role="student",
                    is_active=True
                )
                session.add(user)
                await session.flush()  # Generates user.id

                # Create default free subscription
                sub = Subscription(
                    user_id=user.id,
                    plan_type="free",
                    status="active"
                )
                session.add(sub)
                await session.commit()
        except Exception as e:
            await session.rollback()
            print(f"[Registration Notice] Handled concurrent registration for {telegram_id}: {e}")
            try:
                query = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()
            except Exception:
                pass

    welcome_card = get_welcome_card_text(full_name)

    try:
        # First send quick-access ReplyKeyboardMarkup to keep bottom menu visible on all devices
        await message.answer(
            "🎓 <b>أهلاً بك في أكاديمية Fluence للغة الإنجليزية!</b>\n"
            "تم تفعيل قائمة الأوامر السريعة بالأسفل بنجاح ⬇️",
            reply_markup=get_main_reply_keyboard(),
            parse_mode="HTML"
        )
        # Then present the full prestigious divisions dashboard with interactive inline buttons
        await message.answer(
            welcome_card,
            reply_markup=get_start_hub_inline_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"[Send Message Error] {e}")
        await message.answer(welcome_card, reply_markup=get_start_hub_inline_keyboard())

@start_router.callback_query(F.data == "back_to_main_menu")
async def handle_back_to_main_menu_callback(callback: CallbackQuery):
    """Edits message back to the main academy divisions card."""
    student_name = (callback.from_user.full_name or "Student") if callback.from_user else "Student"
    card_text = get_welcome_card_text(student_name)
    try:
        await callback.message.edit_text(card_text, reply_markup=get_start_hub_inline_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(card_text, reply_markup=get_start_hub_inline_keyboard(), parse_mode="HTML")
    await callback.answer()

@start_router.callback_query(F.data == "open_support_dialog")
async def handle_open_support_dialog_callback(callback: CallbackQuery):
    """Displays contact links with administration and official teacher support via inline query."""
    help_text = (
        "💬 <b>الدعم الأكاديمي والتواصل مع الإدارة | Help & Support</b>\n\n"
        "فريق أكاديمية Fluence هنا لمساعدتك في أي استفسار أو توجيه تعليمي تحتاجه:\n\n"
        "👨‍🏫 <b>التواصل المباشر مع المشرف العام (الأستاذ محمد حسين):</b>\n"
        "👉 @Alzurfi1\n\n"
        "📢 <b>القناة الرسمية للأكاديمية:</b>\n"
        "👉 @FluenceEnglish\n\n"
        "📌 <b>الخدمات المتاحة عبر التواصل المباشر:</b>\n"
        "• التسجيل وحجز المقاعد في الدورات التخصصية (التنافسي / INELT).\n"
        "• طلب استشارة أكاديمية لتحديد المستوى والمسار المناسب.\n"
        "• الإبلاغ عن أي استفسار تقني بخصوص البوت أو الاختبارات.\n\n"
        "يسعدنا تواصلكم دائماً ونتمنى لكم التوفيق والتميز! 🌟"
    )
    keyboard = [
        [InlineKeyboardButton(text="📲 تواصل مع الإدارة | Contact Admin", url="https://t.me/Alzurfi1")],
        [InlineKeyboardButton(text="📢 القناة الرسمية | Official Channel", url="https://t.me/FluenceEnglish")],
        [InlineKeyboardButton(text="🔙 العودة للواجهة الرئيسية | Main Menu", callback_data="back_to_main_menu")]
    ]
    try:
        await callback.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(help_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@start_router.callback_query(F.data == "open_about_fluence")
async def handle_open_about_fluence_callback(callback: CallbackQuery):
    """Displays prestigious overview about Fluence Academy with founder credentials via inline query."""
    about_text = (
        "🌟 <b>مرحباً بك في Fluence English Academy</b> 🌟\n\n"
        "بيئتك التعليمية المتكاملة التي أسسها ويشرف عليها الأستاذ الجامعي <b>Lect. Mohammed Hussein</b>، "
        "المتخصص في اللغة الإنجليزية والأدب العالمي.\n\n"
        "🎯 <b>رؤيتنا والفئة المستهدفة:</b>\n"
        "نهدف إلى تقديم تجربة تعليمية رصينة لتطوير المهارات اللغوية العامة باستخدام مناهج تفاعلية مُعدة خصيصاً "
        "وتخضع للتطوير والتحديث المستمر.\n\n"
        "<b>صُممت برامجنا لتلبي احتياجات:</b>\n"
        "• طلبة الجامعات في مختلف التخصصات.\n"
        "• طلبة وخريجي أقسام اللغة الإنجليزية.\n"
        "• كل من يطمح لتطوير لغته الإنجليزية بشكل عام.\n"
        "• الطلبة الراغبين بالتقديم للدراسات العليا، من خلال كورسات متخصصة في اللغة الأكاديمية، الكتابة البحثية، والتحضير للاختبارات التنافسية والوطنية.\n\n"
        "🌐 <b>مجتمعنا:</b>\n"
        "رحلتك نحو إتقان الإنجليزية تبدأ من هنا، عبر بيئة تفاعلية تدعمك خطوة بخطوة."
    )
    keyboard = [
        [InlineKeyboardButton(text="📢 زيارة القناة الرسمية | Visit Channel", url="https://t.me/FluenceEnglish")],
        [InlineKeyboardButton(text="📚 استكشاف الدورات | Explore Courses", callback_data="back_to_courses")],
        [InlineKeyboardButton(text="🔙 العودة للواجهة الرئيسية | Main Menu", callback_data="back_to_main_menu")]
    ]
    try:
        await callback.message.edit_text(about_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(about_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@start_router.message(F.text.contains("عن الأكاديمية") | F.text.contains("About Fluence"))
async def handle_about_fluence(message: Message):
    """Displays prestigious overview about Fluence Academy with founder credentials."""
    about_text = (
        "🌟 <b>مرحباً بك في Fluence English Academy</b> 🌟\n\n"
        "بيئتك التعليمية المتكاملة التي أسسها ويشرف عليها الأستاذ الجامعي <b>Lect. Mohammed Hussein</b>، "
        "المتخصص في اللغة الإنجليزية والأدب العالمي.\n\n"
        "🎯 <b>رؤيتنا والفئة المستهدفة:</b>\n"
        "نهدف إلى تقديم تجربة تعليمية رصينة لتطوير المهارات اللغوية العامة باستخدام مناهج تفاعلية مُعدة خصيصاً "
        "وتخضع للتطوير والتحديث المستمر.\n\n"
        "<b>صُممت برامجنا لتلبي احتياجات:</b>\n"
        "• طلبة الجامعات في مختلف التخصصات.\n"
        "• طلبة وخريجي أقسام اللغة الإنجليزية.\n"
        "• كل من يطمح لتطوير لغته الإنجليزية بشكل عام.\n"
        "• الطلبة الراغبين بالتقديم للدراسات العليا، من خلال كورسات متخصصة في اللغة الأكاديمية، الكتابة البحثية، والتحضير للاختبارات التنافسية والوطنية.\n\n"
        "🌐 <b>مجتمعنا:</b>\n"
        "رحلتك نحو إتقان الإنجليزية تبدأ من هنا، عبر بيئة تفاعلية تدعمك خطوة بخطوة.\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "🌟 <b>Welcome to Fluence English Academy</b> 🌟\n\n"
        "Your comprehensive learning environment founded and directed by <b>Lect. Mohammed Hussein</b>, "
        "a university professor specialized in English language and global literature.\n\n"
        "🎯 <b>Our Vision & Target Audience:</b>\n"
        "We aim to deliver a rigorous educational experience to develop General English skills using specially designed, "
        "continuously updated curricula.\n\n"
        "<b>Our programs are tailored for:</b>\n"
        "• University students across all majors.\n"
        "• Students and graduates of English departments.\n"
        "• Anyone aiming to improve their general English proficiency.\n"
        "• Prospective postgraduate students, through specialized courses in Academic English, research writing, and competitive/national exam preparation."
    )
    keyboard = [
        [InlineKeyboardButton(text="📢 زيارة القناة الرسمية | Visit Channel", url="https://t.me/FluenceEnglish")],
        [InlineKeyboardButton(text="📚 استكشاف الدورات | Explore Courses", callback_data="back_to_courses")],
        [InlineKeyboardButton(text="🔙 العودة للواجهة الرئيسية | Main Menu", callback_data="back_to_main_menu")]
    ]
    await message.answer(about_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@start_router.message(F.text.contains("الدعم والتواصل") | F.text.contains("Help & Support") | F.text.contains("الدعم الفني"))
async def handle_help_support(message: Message):
    """Provides contact links with administration and official teacher support."""
    help_text = (
        "💬 <b>الدعم الأكاديمي والتواصل مع الإدارة | Help & Support</b>\n\n"
        "فريق أكاديمية Fluence هنا لمساعدتك في أي استفسار أو توجيه تعليمي تحتاجه:\n\n"
        "👨‍🏫 <b>التواصل المباشر مع المشرف العام (الأستاذ محمد حسين):</b>\n"
        "👉 @Alzurfi1\n\n"
        "📢 <b>القناة الرسمية للأكاديمية:</b>\n"
        "👉 @FluenceEnglish\n\n"
        "📌 <b>الخدمات المتاحة عبر التواصل المباشر:</b>\n"
        "• التسجيل وحجز المقاعد في الدورات التخصصية (التنافسي / INELT).\n"
        "• طلب استشارة أكاديمية لتحديد المستوى والمسار المناسب.\n"
        "• الإبلاغ عن أي استفسار تقني بخصوص البوت أو الاختبارات.\n\n"
        "يسعدنا تواصلكم دائماً ونتمنى لكم التوفيق والتميز! 🌟"
    )
    keyboard = [
        [InlineKeyboardButton(text="📲 تواصل مع الإدارة | Contact Admin", url="https://t.me/Alzurfi1")],
        [InlineKeyboardButton(text="📢 القناة الرسمية | Official Channel", url="https://t.me/FluenceEnglish")],
        [InlineKeyboardButton(text="🔙 العودة للواجهة الرئيسية | Main Menu", callback_data="back_to_main_menu")]
    ]
    await message.answer(help_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@start_router.message(F.text == "👤 My Profile")
async def handle_my_profile(message: Message):
    """Displays student profile, subscription plan, and registration date."""
    tg_user = message.from_user
    if not tg_user:
        return

    async with AsyncSessionLocal() as session:
        query = select(User).where(User.telegram_id == tg_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("⚠️ Profile not found. Please type /start to register.")
            return

        # Fetch subscription
        sub_query = select(Subscription).where(Subscription.user_id == user.id)
        sub_result = await session.execute(sub_query)
        sub = sub_result.scalar_one_or_none()

    plan = sub.plan_type.upper() if sub else "FREE"
    status = sub.status.capitalize() if sub else "Active"
    reg_date = user.created_at.strftime("%Y-%m-%d")

    profile_text = (
        f"👤 <b>الملف التعريفي للطالب | Student Profile</b>\n\n"
        f"<b>رقم الطالب:</b> <code>FA-{user.id:04d}</code>\n"
        f"<b>الاسم:</b> {user.full_name}\n"
        f"<b>الرتبة:</b> {user.role.capitalize()}\n"
        f"<b>الخطة:</b> {plan} ({status})\n"
        f"<b>تاريخ الانضمام:</b> {reg_date}\n\n"
        f"نتمنى لك دوام التقدم والنجاح! 🌟"
    )
    await message.answer(profile_text, parse_mode="HTML")

@start_router.callback_query(F.data == "check_channel_joined")
async def handle_check_channel_callback(callback: CallbackQuery):
    """Verifies channel membership when user clicks the verification button."""
    bot = callback.bot
    if not bot:
        await callback.answer("System error.", show_alert=True)
        return

    tg_user = callback.from_user
    is_member, msg = await check_user_channel_membership(bot, tg_user.id)
    channel = settings.REQUIRED_TELEGRAM_CHANNEL or "@FluenceEnglish"

    if is_member:
        # Ensure user is registered in the database
        async with AsyncSessionLocal() as session:
            try:
                query = select(User).where(User.telegram_id == tg_user.id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()

                if not user:
                    user = User(
                        telegram_id=tg_user.id,
                        username=tg_user.username,
                        full_name=tg_user.full_name or "Student",
                        role="student",
                        is_active=True
                    )
                    session.add(user)
                    await session.flush()

                    sub = Subscription(
                        user_id=user.id,
                        plan_type="free",
                        status="active"
                    )
                    session.add(sub)
                    await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"[Verification Notice] Concurrent user registration handled: {e}")

        await callback.answer("🎉 تم التحقق من اشتراكك بنجاح! أهلاً بك معنا.", show_alert=True)

        welcome_card = get_welcome_card_text(tg_user.full_name or "Student")

        try:
            if callback.message:
                await callback.message.delete()
        except Exception:
            pass

        if callback.message:
            await callback.message.answer(
                "🎓 <b>تم التحقق بنجاح! تم تفعيل قائمة الأوامر بالأسفل بنجاح ⬇️</b>",
                reply_markup=get_main_reply_keyboard(),
                parse_mode="HTML"
            )
            await callback.message.answer(
                welcome_card,
                reply_markup=get_start_hub_inline_keyboard(),
                parse_mode="HTML"
            )
    else:
        await callback.answer(
            f"⚠️ لم يتم العثور على اشتراكك في القناة بعد!\n\nيرجى التأكد من الانضمام إلى {channel} ثم الضغط على تحقق مرة أخرى.",
            show_alert=True
        )
