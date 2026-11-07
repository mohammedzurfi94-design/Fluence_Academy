import asyncio
import os
import random
import requests
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from datetime import datetime, timezone

from app.database.connection import AsyncSessionLocal
from app.database.models import User, Quiz, QuizQuestion, QuizAnswer, QuizAttempt, StudentProgress
from app.core.config import settings

try:
    from app.services.scheduler_service import get_today_lesson, send_daily_lesson_to_user
except ImportError:
    def get_today_lesson(force_refresh=False):
        return {
            "topic": "Daily English",
            "info": "Welcome to Fluence Academy!",
            "questions": []
        }
    async def send_daily_lesson_to_user(bot, chat_id, lesson, send_voice=True):
        pass
