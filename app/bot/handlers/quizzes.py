import asyncio
import os
import random
import requests
import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from datetime import datetime, timezone

from app.database.connection import AsyncSessionLocal
from app.database.models import User, Quiz, QuizQuestion, QuizAnswer, QuizAttempt, StudentProgress
from app.core.config import settings

# 1. Initialize quizzes_router immediately at the top level
quizzes_router = Router(name="quizzes_router")

try:
    from app.services.ai_service import get_today_lesson, send_daily_lesson_to_user, create_certificate_pdf
except Exception:
    try:
        from app.services.scheduler_service import get_today_lesson, send_daily_lesson_to_user
        from app.services.certificate_service import create_certificate_pdf
    except Exception:
        def get_today_lesson(force_refresh=False):
            return {
                "topic": "Daily English",
                "info": "Welcome to Fluence Academy!",
                "questions": []
            }
        async def send_daily_lesson_to_user(bot, chat_id, lesson, send_voice=True):
            pass
        create_certificate_pdf = None

def save_to_notion(first_name, username, score, level):
    url = "https://api.notion.com/v1/pages"
    
    token = os.getenv("NOTION_API_TOKEN") or getattr(settings, "NOTION_API_TOKEN", None) or "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"
    database_id = os.getenv("NOTION_DATABASE_ID") or getattr(settings, "NOTION_DATABASE_ID", None) or "7ae3e7572bf54b198a13816b43c90e05"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    username_text = f"@{username}" if username else "لا يوجد معرف"

    data = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {
                "title": [{"text": {"content": first_name or "طالب مجهول"}}]
            },
            "Username": {
                "rich_text": [{"text": {"content": username_text}}]
            },
            "Score": {
                "number": score
            },
            "Level": {
                "rich_text": [{"text": {"content": str(level)}}]
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code not in [200, 201]:
            print(f"Notion Error: {response.text}")
        else:
            print(f"Notion Success: Saved placement result for {first_name} (Score: {score}/20, Level: {level})")
    except Exception as e:
        print(f"Failed to connect to Notion: {e}")

@quizzes_router.callback_query(F.data.startswith("start_quiz_"))
async def handle_start_quiz(callback: CallbackQuery):
    """Starts the quiz for a given lesson."""
    lesson_id = int(callback.data.split("_")[-1])

    async with AsyncSessionLocal() as session:
        q_query = select(Quiz).where(Quiz.lesson_id == lesson_id)
        q_result = await session.execute(q_query)
        quiz = q_result.scalar_one_or_none()

        if not quiz:
            await callback.answer("No quiz available for this lesson yet.", show_alert=True)
            return

        quest_query = select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.order_index)
        quest_result = await session.execute(quest_query)
        questions = quest_result.scalars().all()

        if not questions:
            await
