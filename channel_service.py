from aiogram import Bot
from app.core.config import settings

async def check_user_channel_membership(bot: Bot, user_id: int) -> tuple[bool, str]:
    """
    Checks if a Telegram user is a member of the configured academy channel.
    Returns:
        (is_member: bool, message: str)
    """
    channel = settings.REQUIRED_TELEGRAM_CHANNEL
    if not channel or not channel.strip():
        return True, "Channel verification disabled."

    channel = channel.strip()
    if not channel.startswith("@") and not channel.startswith("-100"):
        channel = f"@{channel}"

    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        if member.status in ["creator", "administrator", "member", "restricted"]:
            return True, "Member verified."
        else:
            return False, f"User is not a member (status: {member.status})."
    except Exception as e:
        error_msg = str(e).lower()
        if "chat not found" in error_msg or "bot is not a member" in error_msg:
            print(f"[ChannelCheck Warning] Bot cannot check membership of {channel}. Ensure @Fluenceacademybot is added as Administrator to {channel}!")
            # Gracefully allow or inform so testing is not blocked
            return False, "Bot is not an admin in the channel yet."
        return False, f"Verification error: {e}"
