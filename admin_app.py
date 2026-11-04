import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func, desc

from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.database.connection import AsyncSessionLocal
from app.database.models import (
    User, Subscription, Course, Lesson, LessonMaterial, Quiz, QuizQuestion, QuizAnswer, QuizAttempt, StudentProgress, Announcement
)
from app.dashboard.auth import get_current_user_from_cookie, require_admin_or_teacher
from app.bot.bot_instance import create_bot

# Setup FastAPI App & Templates
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "dashboard" / "templates"))

admin_app = FastAPI(title="Fluence Academy Admin Portal")

# -------------------------------------------------------------
# 0. Health Check Route for Render & Monitoring
# -------------------------------------------------------------
@admin_app.get("/health")
async def health_check():
    return {"status": "ok", "app": "Fluence Academy"}

# -------------------------------------------------------------
# 1. Authentication Routes
# -------------------------------------------------------------
@admin_app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = await get_current_user_from_cookie(request)
    if user and user.role in ["admin", "teacher"]:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})

@admin_app.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    async with AsyncSessionLocal() as session:
        query = select(User).where(User.username == username.strip(), User.is_active == True)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Invalid username or password."},
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    if user.role not in ["admin", "teacher"]:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Access denied: Admin or Teacher account required."},
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Create session token
    token = create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="fluence_access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24, # 24 hours
        samesite="lax"
    )
    return response

@admin_app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="fluence_access_token")
    return response

# -------------------------------------------------------------
# 2. Overview Dashboard Route
# -------------------------------------------------------------
@admin_app.get("/", response_class=HTMLResponse)
async def dashboard_overview(request: Request, user: User = Depends(require_admin_or_teacher)):
    async with AsyncSessionLocal() as session:
        # Total counts
        total_students = (await session.execute(select(func.count(User.id)).where(User.role == "student"))).scalar() or 0
        total_courses = (await session.execute(select(func.count(Course.id)))).scalar() or 0
        total_lessons = (await session.execute(select(func.count(Lesson.id)))).scalar() or 0
        total_attempts = (await session.execute(select(func.count(QuizAttempt.id)))).scalar() or 0

        # Recent students
        students_q = select(User).where(User.role == "student").order_by(desc(User.created_at)).limit(5)
        recent_students = (await session.execute(students_q)).scalars().all()

        # Recent attempts
        attempts_q = select(QuizAttempt).order_by(desc(QuizAttempt.completed_at)).limit(5)
        recent_attempts = (await session.execute(attempts_q)).scalars().all()

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "user": user,
        "active_page": "dashboard",
        "total_students": total_students,
        "total_courses": total_courses,
        "total_lessons": total_lessons,
        "total_attempts": total_attempts,
        "recent_students": recent_students,
        "recent_attempts": recent_attempts
    })

# -------------------------------------------------------------
# 3. Students & Subscriptions Routes
# -------------------------------------------------------------
@admin_app.get("/students", response_class=HTMLResponse)
async def students_list(request: Request, user: User = Depends(require_admin_or_teacher)):
    async with AsyncSessionLocal() as session:
        q = select(User).where(User.role == "student").order_by(desc(User.created_at))
        students = (await session.execute(q)).scalars().all()

        students_data = []
        for s in students:
            sub_q = select(Subscription).where(Subscription.user_id == s.id)
            sub = (await session.execute(sub_q)).scalar_one_or_none()
            students_data.append({"student": s, "sub": sub})

    return templates.TemplateResponse(request=request, name="students.html", context={
        "user": user,
        "active_page": "students",
        "students": students,
        "students_data": students_data
    })

@admin_app.post("/students/{student_id}/update-plan")
async def update_student_plan(
    student_id: int,
    plan_type: str = Form(...),
    user: User = Depends(require_admin_or_teacher)
):
    async with AsyncSessionLocal() as session:
        sub_q = select(Subscription).where(Subscription.user_id == student_id)
        sub = (await session.execute(sub_q)).scalar_one_or_none()

        if sub:
            sub.plan_type = plan_type
            sub.status = "active"
        else:
            new_sub = Subscription(user_id=student_id, plan_type=plan_type, status="active")
            session.add(new_sub)

        await session.commit()

    return RedirectResponse(url="/students", status_code=status.HTTP_302_FOUND)

# -------------------------------------------------------------
# 4. Courses & Lessons Routes
# -------------------------------------------------------------
@admin_app.get("/courses", response_class=HTMLResponse)
async def courses_list(request: Request, user: User = Depends(require_admin_or_teacher)):
    async with AsyncSessionLocal() as session:
        courses = (await session.execute(select(Course).order_by(desc(Course.created_at)))).scalars().all()
        courses_data = []
        for c in courses:
            count_q = select(func.count(Lesson.id)).where(Lesson.course_id == c.id)
            lesson_count = (await session.execute(count_q)).scalar() or 0
            courses_data.append({"course": c, "lesson_count": lesson_count})

    return templates.TemplateResponse(request=request, name="courses.html", context={
        "user": user,
        "active_page": "courses",
        "courses_data": courses_data
    })

@admin_app.post("/courses/create")
async def create_course(
    request: Request,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    required_telegram_channel: Optional[str] = Form(None),
    is_published: Optional[bool] = Form(False),
    requires_subscription: Optional[bool] = Form(False),
    user: User = Depends(require_admin_or_teacher)
):
    async with AsyncSessionLocal() as session:
        new_course = Course(
            title=title.strip(),
            description=description.strip() if description else None,
            teacher_id=user.id,
            is_published=is_published,
            requires_subscription=requires_subscription,
            required_telegram_channel=required_telegram_channel.strip() if required_telegram_channel else None
        )
        session.add(new_course)
        await session.commit()

    return RedirectResponse(url="/courses", status_code=status.HTTP_302_FOUND)

@admin_app.get("/courses/{course_id}", response_class=HTMLResponse)
async def course_detail(
    course_id: int,
    request: Request,
    user: User = Depends(require_admin_or_teacher)
):
    async with AsyncSessionLocal() as session:
        course = (await session.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        lessons = (await session.execute(select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.order_index))).scalars().all()

        lessons_data = []
        for l in lessons:
            mats = (await session.execute(select(LessonMaterial).where(LessonMaterial.lesson_id == l.id))).scalars().all()
            lessons_data.append({"lesson": l, "materials": mats})

    return templates.TemplateResponse(request=request, name="course_detail.html", context={
        "user": user,
        "active_page": "courses",
        "course": course,
        "lessons_data": lessons_data
    })

@admin_app.post("/courses/{course_id}/lessons/create")
async def create_lesson(
    course_id: int,
    title: str = Form(...),
    order_index: int = Form(1),
    content_text: str = Form(...),
    is_preview: Optional[bool] = Form(False),
    user: User = Depends(require_admin_or_teacher)
):
    async with AsyncSessionLocal() as session:
        new_lesson = Lesson(
            course_id=course_id,
            title=title.strip(),
            order_index=order_index,
            content_text=content_text.strip(),
            is_preview=is_preview
        )
        session.add(new_lesson)
        await session.commit()

    return RedirectResponse(url=f"/courses/{course_id}", status_code=status.HTTP_302_FOUND)

@admin_app.post("/lessons/{lesson_id}/upload-pdf")
async def upload_lesson_pdf(
    lesson_id: int,
    file: UploadFile = File(...),
    user: User = Depends(require_admin_or_teacher)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    storage_dir = BASE_DIR / "storage" / "pdfs"
    storage_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"lesson_{lesson_id}_{Path(file.filename).name}"
    file_path = storage_dir / safe_name

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    async with AsyncSessionLocal() as session:
        lesson = (await session.execute(select(Lesson).where(Lesson.id == lesson_id))).scalar_one_or_none()
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        mat = LessonMaterial(
            lesson_id=lesson_id,
            title=file.filename,
            file_type="pdf",
            file_path=str(file_path),
            file_size_bytes=file_size
        )
        session.add(mat)
        await session.commit()
        course_id = lesson.course_id

    return RedirectResponse(url=f"/courses/{course_id}", status_code=status.HTTP_302_FOUND)

# -------------------------------------------------------------
# 5. Quizzes & Exam Results Routes
# -------------------------------------------------------------
@admin_app.get("/quizzes", response_class=HTMLResponse)
async def quizzes_overview(request: Request, user: User = Depends(require_admin_or_teacher)):
    async with AsyncSessionLocal() as session:
        quizzes = (await session.execute(select(Quiz))).scalars().all()
        quizzes_data = []
        for q in quizzes:
            course = (await session.execute(select(Course).where(Course.id == q.course_id))).scalar_one_or_none()
            q_count = (await session.execute(select(func.count(QuizQuestion.id)).where(QuizQuestion.quiz_id == q.id))).scalar() or 0
            att_count = (await session.execute(select(func.count(QuizAttempt.id)).where(QuizAttempt.quiz_id == q.id))).scalar() or 0
            quizzes_data.append({
                "quiz": q,
                "course_title": course.title if course else "General",
                "question_count": q_count,
                "attempt_count": att_count
            })

        # All attempts with student & quiz names
        attempts_raw = (await session.execute(select(QuizAttempt).order_by(desc(QuizAttempt.completed_at)))).scalars().all()
        attempts = []
        for a in attempts_raw:
            st = (await session.execute(select(User).where(User.id == a.student_id))).scalar_one_or_none()
            qz = (await session.execute(select(Quiz).where(Quiz.id == a.quiz_id))).scalar_one_or_none()
            attempts.append({
                "id": a.id,
                "student_id": a.student_id,
                "student_name": st.full_name if st else f"Student #{a.student_id}",
                "quiz_title": qz.title if qz else f"Quiz #{a.quiz_id}",
                "score_percentage": a.score_percentage,
                "passed": a.passed,
                "completed_at": a.completed_at
            })

    return templates.TemplateResponse(request=request, name="quizzes.html", context={
        "user": user,
        "active_page": "quizzes",
        "quizzes_data": quizzes_data,
        "attempts": attempts
    })

@admin_app.post("/courses/{course_id}/quizzes/create")
async def create_course_quiz(
    course_id: int,
    title: str = Form(...),
    pass_percentage: float = Form(70.0),
    question_text: str = Form(...),
    option_a: str = Form(...),
    option_b: str = Form(...),
    option_c: str = Form(...),
    option_d: str = Form(...),
    correct_option: str = Form("a"),
    explanation: Optional[str] = Form(None),
    lesson_id: Optional[int] = Form(None),
    user: User = Depends(require_admin_or_teacher)
):
    async with AsyncSessionLocal() as session:
        # Create Quiz
        quiz = Quiz(
            course_id=course_id,
            lesson_id=lesson_id if lesson_id and lesson_id > 0 else None,
            title=title.strip(),
            pass_percentage=pass_percentage,
            is_exam=False
        )
        session.add(quiz)
        await session.flush()

        # Create Question
        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text=question_text.strip(),
            order_index=1,
            points=10,
            explanation=explanation.strip() if explanation else None
        )
        session.add(question)
        await session.flush()

        # Add Answers
        options = [
            ("a", option_a),
            ("b", option_b),
            ("c", option_c),
            ("d", option_d)
        ]
        for key, text in options:
            ans = QuizAnswer(
                question_id=question.id,
                answer_text=text.strip(),
                is_correct=(correct_option.lower() == key)
            )
            session.add(ans)

        await session.commit()

    return RedirectResponse(url=f"/courses/{course_id}", status_code=status.HTTP_302_FOUND)

# -------------------------------------------------------------
# 6. Broadcast Announcements Routes
# -------------------------------------------------------------
@admin_app.get("/announcements", response_class=HTMLResponse)
async def announcements_page(request: Request, user: User = Depends(require_admin_or_teacher)):
    async with AsyncSessionLocal() as session:
        ann_q = select(Announcement).order_by(desc(Announcement.sent_at))
        announcements = (await session.execute(ann_q)).scalars().all()

    return templates.TemplateResponse(request=request, name="announcements.html", context={
        "user": user,
        "active_page": "announcements",
        "announcements": announcements,
        "channel": settings.REQUIRED_TELEGRAM_CHANNEL or "@FluenceEnglish",
        "message": None
    })

@admin_app.post("/announcements/broadcast")
async def broadcast_announcement(
    request: Request,
    title: str = Form(...),
    message_text: str = Form(...),
    target: str = Form("both"),
    user: User = Depends(require_admin_or_teacher)
):
    bot = create_bot()
    delivered_count = 0

    formatted_msg = (
        f"📢 <b>ACADEMY ANNOUNCEMENT</b>\n\n"
        f"<b>{title.strip()}</b>\n\n"
        f"{message_text.strip()}\n\n"
        f"<i>— Fluence Academy Team</i>"
    )

    try:
        # 1. Send to Telegram Channel
        if target in ["channel", "both"] and settings.REQUIRED_TELEGRAM_CHANNEL:
            try:
                await bot.send_message(
                    chat_id=settings.REQUIRED_TELEGRAM_CHANNEL,
                    text=formatted_msg,
                    parse_mode="HTML"
                )
                delivered_count += 1
            except Exception as e:
                print(f"[Broadcast Error Channel] {e}")

        # 2. Send to all registered students
        if target in ["students", "both"]:
            async with AsyncSessionLocal() as session:
                students_q = select(User).where(User.telegram_id.is_not(None))
                students = (await session.execute(students_q)).scalars().all()

                for s in students:
                    try:
                        await bot.send_message(
                            chat_id=s.telegram_id,
                            text=formatted_msg,
                            parse_mode="HTML"
                        )
                        delivered_count += 1
                    except Exception as e:
                        print(f"[Broadcast Error User {s.telegram_id}] {e}")

        # Record in database
        async with AsyncSessionLocal() as session:
            ann = Announcement(
                author_id=user.id,
                title=title.strip(),
                message_text=message_text.strip()
            )
            session.add(ann)
            await session.commit()
    finally:
        await bot.session.close()

    async with AsyncSessionLocal() as session:
        ann_q = select(Announcement).order_by(desc(Announcement.sent_at))
        announcements = (await session.execute(ann_q)).scalars().all()

    return templates.TemplateResponse(request=request, name="announcements.html", context={
        "user": user,
        "active_page": "announcements",
        "announcements": announcements,
        "channel": settings.REQUIRED_TELEGRAM_CHANNEL or "@FluenceEnglish",
        "message": f"Broadcast sent successfully! Delivered to {delivered_count} recipient(s)."
    })

# -------------------------------------------------------------
# 7. Database Backups & Recovery Routes
# -------------------------------------------------------------
@admin_app.get("/backups", response_class=HTMLResponse)
async def backups_page(request: Request, user: User = Depends(require_admin_or_teacher)):
    backup_dir = BASE_DIR / "storage" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    backups = []
    for file in sorted(backup_dir.glob("*.db"), key=os.path.getmtime, reverse=True):
        stat = file.stat()
        created_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        size_kb = round(stat.st_size / 1024, 1)
        backups.append({
            "name": file.name,
            "size_kb": size_kb,
            "created_time": created_time
        })

    return templates.TemplateResponse(request=request, name="backups.html", context={
        "user": user,
        "active_page": "backups",
        "backups": backups
    })

@admin_app.post("/backups/create")
async def create_backup(user: User = Depends(require_admin_or_teacher)):
    db_source = BASE_DIR / "storage" / "fluence.db"
    backup_dir = BASE_DIR / "storage" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    if db_source.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dest = backup_dir / f"fluence_backup_{timestamp}.db"
        shutil.copy2(db_source, backup_dest)

    return RedirectResponse(url="/backups", status_code=status.HTTP_302_FOUND)

@admin_app.get("/backups/download/{filename}")
async def download_backup(filename: str, user: User = Depends(require_admin_or_teacher)):
    backup_path = BASE_DIR / "storage" / "backups" / filename
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")
    return FileResponse(backup_path, filename=filename, media_type="application/octet-stream")
