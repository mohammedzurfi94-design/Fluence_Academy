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
        f"👤 <b>Student Profile</b>\n\n"
        f"<b>Student ID:</b> <code>FA-{user.id:04d}</code>\n"
        f"<b>Name:</b> {user.full_name}\n"
        f"<b>Role:</b> {user.role.capitalize()}\n"
        f"<b>Subscription Plan:</b> {plan} ({status})\n"
        f"<b>Joined:</b> {reg_date}\n\n"
        f"Keep up the great work! 🌟"
    )

    await message.answer(profile_text, parse_mode="HTML")

@start_router.message(F.text == "📢 Official Channel")
async def handle_channel_info(message: Message):
    """Directs students to the official academy channel."""
    channel = settings.REQUIRED_TELEGRAM_CHANNEL or "@FluenceAcademy"
    clean_channel = channel.replace("@", "")
    url = f"https://t.me/{clean_channel}"

    text = (
        f"📢 <b>Fluence Academy Official Channel</b>\n\n"
        f"Stay updated with new lesson releases, live sessions, announcements, and study tips!\n\n"
        f"👉 <b>Channel:</b> {channel}"
    )
    await message.answer(text, reply_markup=get_channel_join_keyboard(url), parse_mode="HTML")

@start_router.message(F.text == "❓ Help & Support")
async def handle_help_support(message: Message):
    """Provides help contact and guidance."""
    help_text = (
        f"❓ <b>Fluence Academy Support</b>\n\n"
        f"Need assistance with a course, quiz, or your account?\n\n"
        f"• If a lesson won't open, ensure you've joined our channel.\n"
        f"• For administrative inquiries, contact our academy team.\n\n"
        f"Happy learning! 🚀"
    )
    await message.answer(help_text, parse_mode="HTML")

@start_router.callback_query(F.data == "check_channel_joined")
async def handle_check_channel_callback(callback: CallbackQuery):
    """Verifies channel membership when user clicks the verification button."""
    bot = callback.bot
    if not bot:
        await callback.answer("System error.", show_alert=True)
        return

    is_member, msg = await check_user_channel_membership(bot, callback.from_user.id)
    channel = settings.REQUIRED_TELEGRAM_CHANNEL or "@FluenceEnglish"

    if is_member:
        await callback.answer("🎉 Verification successful! Welcome aboard!", show_alert=True)
        await callback.message.edit_text(
            f"✅ <b>Channel Membership Confirmed!</b>\n\n"
            f"Thank you for joining <b>{channel}</b>.\n"
            f"You now have access to all public courses and study resources!\n\n"
            f"Choose an option below to start learning:",
            parse_mode="HTML"
        )
    else:
        await callback.answer(
            f"⚠️ Membership not detected yet!\n\nPlease make sure you joined {channel}, then tap this button again.",
            show_alert=True
        )
