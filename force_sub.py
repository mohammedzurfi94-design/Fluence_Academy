from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from app.core.config import settings
from app.services.channel_service import check_user_channel_membership
from app.bot.keyboards.main_menu import get_channel_join_keyboard

class ForceSubscribeMiddleware(BaseMiddleware):
    """
    Middleware that enforces channel subscription before allowing users
    to interact with the bot.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        channel = settings.REQUIRED_TELEGRAM_CHANNEL
        if not channel or not channel.strip():
            return await handler(event, data)

        bot = data.get("bot")
        if not bot:
            return await handler(event, data)

        user = None
        is_callback = isinstance(event, CallbackQuery)
        is_message = isinstance(event, Message)

        if is_message:
            if event.chat.type != "private":
                return await handler(event, data)
            user = event.from_user
        elif is_callback:
            # Allow the check subscription callback to proceed to its handler
            if event.data == "check_channel_joined":
                return await handler(event, data)
            if event.message and event.message.chat.type != "private":
                return await handler(event, data)
            user = event.from_user

        if not user:
            return await handler(event, data)

        # Check membership
        is_member, _ = await check_user_channel_membership(bot, user.id)
        if is_member:
            return await handler(event, data)

        # If not a member, block and request subscription
        clean_channel = channel.replace("@", "")
        channel_url = f"https://t.me/{clean_channel}"
        prompt_text = (
            f"⚠️ <b>عذراً، يجب عليك الاشتراك في القناة أولاً!</b>\n\n"
            f"للاستفادة من محتوى <b>Fluence Academy</b> والوصول إلى كافة الكورسات والدروس والاختبارات، "
            f"يرجى الانضمام إلى قناتنا الرسمية:\n"
            f"👉 <b>{channel}</b>\n\n"
            f"اضغط على الزر أدناه للانضمام، ثم اضغط على <b>«تحقق من الاشتراك ✅»</b> للبدء فوراً! 👇"
        )

        if is_message:
            await event.answer(
                prompt_text,
                reply_markup=get_channel_join_keyboard(channel_url),
                parse_mode="HTML"
            )
        elif is_callback:
            await event.answer(
                "⚠️ يجب عليك الاشتراك في القناة الرسمية أولاً لتتمكن من استخدام البوت!",
                show_alert=True
            )
            try:
                await event.message.answer(
                    prompt_text,
                    reply_markup=get_channel_join_keyboard(channel_url),
                    parse_mode="HTML"
                )
            except Exception:
                pass

        return None
