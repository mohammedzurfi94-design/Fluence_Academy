from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Returns the main bottom keyboard for easy student navigation."""
    keyboard = [
        [KeyboardButton(text="📚 Browse Courses"), KeyboardButton(text="📖 My Learning")],
        [KeyboardButton(text="📝 Quizzes & Grades"), KeyboardButton(text="👤 My Profile")],
        [KeyboardButton(text="📢 Official Channel"), KeyboardButton(text="❓ Help & Support")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="Select an option from the menu..."
    )

def get_channel_join_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    """Returns an inline button asking student to join the required channel."""
    keyboard = [
        [InlineKeyboardButton(text="📢 Join Official Channel", url=channel_url)],
        [InlineKeyboardButton(text="✅ I Have Joined, Continue", callback_data="check_channel_joined")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
