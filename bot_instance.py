from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.core.config import settings
from app.bot.handlers.start import start_router
from app.bot.handlers.courses import courses_router
from app.bot.handlers.quizzes import quizzes_router
from app.bot.handlers.ai_tutor import ai_router
from app.bot.middlewares.force_sub import ForceSubscribeMiddleware

def create_bot() -> Bot:
    """Creates and returns the aiogram Bot instance."""
    return Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

def create_dispatcher() -> Dispatcher:
    """Creates the Dispatcher and registers all routers and middlewares."""
    dp = Dispatcher()

    # Register Force Subscribe Middleware
    force_sub_middleware = ForceSubscribeMiddleware()
    dp.message.outer_middleware(force_sub_middleware)
    dp.callback_query.outer_middleware(force_sub_middleware)

    # Register handlers
    dp.include_router(start_router)
    dp.include_router(courses_router)
    dp.include_router(quizzes_router)
    dp.include_router(ai_router)

    return dp
