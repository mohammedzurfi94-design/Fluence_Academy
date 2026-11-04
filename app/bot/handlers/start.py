from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from datetime import datetime

from app.database.connection import AsyncSessionLocal
from app.database.models import User, Subscription
from app.bot.keyboards.main_menu import get_main_reply_keyboard, get_channel_join_keyboard
from app.core.config import settings
from app.services.channel_service import check_user_channel_membership

start_router = Router(name="start_router")

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
            # Re-fetch user safely
            try:
                query = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()
            except Exception:
                pass

    welcome_text = (
        f"مرحباً بك في <b>Fluence Academy</b>! 🎓\n"
        f"معك الأستاذ محمد حسين.\n"
        f"رحلتك نحو إتقان اللغة الإنجليزية تبدأ من هنا.\n\n"
        f"لقد صممنا هذه المنصة لتكون بيئتك الأكاديمية المتكاملة. يمكنك من خلال القائمة أدناه:\n"
        f"📚 تصفح الكورسات والدروس التفاعلية\n"
        f"📄 تحميل الملخصات والمواد الدراسية\n"
        f"📝 أداء الاختبارات وتقييم مستواك بدقة\n"
        f"🏆 متابعة تقدمك والحصول على شهادات الإتمام\n\n"
        f"اختر القسم الذي تود البدء به من القائمة بالأسفل لننطلق معاً! 👇"
    )

    try:
        await message.answer(
            welcome_text,
            reply_markup=get_main_reply_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"[Send Message Error] {e}")

@start_router.message(F.text.in_(["✨ عن الأكاديمية | About Fluence"]))
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
        [InlineKeyboardButton(text="📚 استكشاف الدورات | Explore Courses", callback_data="back_to_courses")]
    ]
    await message.answer(about_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@start_router.message(F.text.in_(["💬 الدعم والتواصل | Help & Support", "❓ Help & Support"]))
async def handle_help_support(message: Message):
    """Provides contact links with administration and official teacher support."""
    help_text = (
        "💬 <b>الدعم الفني والتواصل مع الإدارة | Help & Support</b>\n\n"
        "فريق أكاديمية Fluence هنا لمساعدتك في أي استفسار أو توجيه تعليمي تحتاجه:\n\n"
        "👨‍🏫 <b>التواصل المباشر مع الأستاذ محمد حسين:</b>\n"
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
        [InlineKeyboardButton(text="📢 القناة الرسمية | Official Channel", url="https://t.me/FluenceEnglish")]
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

        welcome_text = (
            f"مرحباً بك في <b>Fluence Academy</b>! 🎓\n"
            f"معك الأستاذ محمد حسين.\n"
            f"رحلتك نحو إتقان اللغة الإنجليزية تبدأ من هنا.\n\n"
            f"لقد صممنا هذه المنصة لتكون بيئتك الأكاديمية المتكاملة. يمكنك من خلال القائمة أدناه:\n"
            f"📚 تصفح الكورسات والدروس التفاعلية\n"
            f"📄 تحميل الملخصات والمواد الدراسية\n"
            f"📝 أداء الاختبارات وتقييم مستواك بدقة\n"
            f"🏆 متابعة تقدمك والحصول على شهادات الإتمام\n\n"
            f"اختر القسم الذي تود البدء به من القائمة بالأسفل لننطلق معاً! 👇"
        )

        try:
            if callback.message:
                await callback.message.delete()
        except Exception:
            pass

        if callback.message:
            await callback.message.answer(
                welcome_text,
                reply_markup=get_main_reply_keyboard(),
                parse_mode="HTML"
            )
    else:
        await callback.answer(
            f"⚠️ لم يتم العثور على اشتراكك في القناة بعد!\n\nيرجى التأكد من الانضمام إلى {channel} ثم الضغط على تحقق مرة أخرى.",
            show_alert=True
        )
