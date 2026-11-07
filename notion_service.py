import os
import logging
import requests
from app.core.config import settings

logger = logging.getLogger(__name__)

# Fallback environment access
DEFAULT_NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN", "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")
DEFAULT_NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "7ae3e7572bf54b198a13816b43c90e05")

def save_to_notion(first_name: str, username: str | None, score: int, level: str) -> None:
    """
    Saves placement test result to Notion database with Fluence Academy credentials.
    """
    send_placement_result_to_notion(
        student_name=first_name,
        username=username,
        score=score,
        level=level,
        api_token=DEFAULT_NOTION_API_TOKEN,
        database_id=DEFAULT_NOTION_DATABASE_ID
    )

def send_placement_result_to_notion(
    student_name: str,
    username: str | None,
    score: int,
    level: str,
    api_token: str | None = None,
    database_id: str | None = None
) -> bool:
    """
    Sends student's placement test results to a Notion database using Notion API.

    Notion Database Columns expected:
    - Name (title): Student full name or first name
    - Username (rich_text): Telegram @username
    - Score (number): Test score out of 20
    - Level (select or rich_text): CEFR Level (e.g. B2, C1)
    """
    token = api_token or getattr(settings, "NOTION_API_TOKEN", None) or DEFAULT_NOTION_API_TOKEN
    db_id = database_id or getattr(settings, "NOTION_DATABASE_ID", None) or DEFAULT_NOTION_DATABASE_ID

    # Strip any brackets or surrounding quotes if pasted literally
    if token:
        token = token.strip().strip("[]").strip("'\"")
    if db_id:
        db_id = db_id.strip().strip("[]").strip("'\"")

    if not token or not db_id or "ضع مفتاح" in token or "ضع معرف" in db_id or "your_" in token.lower():
        logger.warning("[Notion API] NOTION_API_TOKEN or NOTION_DATABASE_ID not configured yet. Skipping Notion record creation.")
        return False

    # Format username
    clean_username = ""
    if username:
        clean_username = username if username.startswith("@") else f"@{username}"

    # Extract short level code (e.g., 'B2' from '📕 Intermediate & Upper (B2)')
    clean_level = str(level).strip()
    if "(" in clean_level and ")" in clean_level:
        short_code = clean_level.split("(")[-1].split(")")[0].strip()
    else:
        short_code = clean_level

    endpoint_url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # Attempt 1: Level as 'select' property
    payload_select = {
        "parent": {"database_id": db_id},
        "properties": {
            "Name": {
                "title": [
                    {"text": {"content": student_name or "Student"}}
                ]
            },
            "Username": {
                "rich_text": [
                    {"text": {"content": clean_username}}
                ]
            },
            "Score": {
                "number": score
            },
            "Level": {
                "select": {"name": short_code.replace(",", "-")}
            }
        }
    }

    try:
        response = requests.post(endpoint_url, headers=headers, json=payload_select, timeout=8)
        if response.status_code in [200, 201]:
            logger.info(f"[Notion API] Successfully created page for {student_name} (Score: {score}/20, Level: {short_code})")
            return True

        # Attempt 2: If 'select' failed (e.g. column is rich_text in Notion), retry as 'rich_text'
        payload_text = {
            "parent": {"database_id": db_id},
            "properties": {
                "Name": {
                    "title": [
                        {"text": {"content": student_name or "Student"}}
                    ]
                },
                "Username": {
                    "rich_text": [
                        {"text": {"content": clean_username}}
                    ]
                },
                "Score": {
                    "number": score
                },
                "Level": {
                    "rich_text": [
                        {"text": {"content": clean_level}}
                    ]
                }
            }
        }
        retry_resp = requests.post(endpoint_url, headers=headers, json=payload_text, timeout=8)
        if retry_resp.status_code in [200, 201]:
            logger.info(f"[Notion API] Successfully created page with rich_text Level for {student_name}")
            return True
        else:
            logger.error(f"[Notion API Error] Status {retry_resp.status_code}: {retry_resp.text}")
            return False

    except Exception as e:
        logger.error(f"[Notion API Exception] Failed to send page to Notion: {e}")
        return False
