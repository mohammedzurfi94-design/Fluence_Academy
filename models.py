from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, Float, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from app.database.connection import Base

def utc_now():
    return datetime.now(timezone.utc)

# 1. Users Table (Students, Teachers, Admins)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True)
    username = Column(String(100), nullable=True)
    full_name = Column(String(150), nullable=False)
    hashed_password = Column(String(255), nullable=True)  # For Admin/Teacher web login
    role = Column(String(50), default="student", nullable=False)  # 'admin', 'teacher', 'student'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    progress = relationship("StudentProgress", back_populates="student", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="student", cascade="all, delete-orphan")
    grades = relationship("Grade", back_populates="student", cascade="all, delete-orphan")

# 2. Subscriptions Table
class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_type = Column(String(50), default="free", nullable=False)  # 'free', 'standard', 'vip'
    status = Column(String(50), default="active", nullable=False)   # 'active', 'expired', 'cancelled'
    start_date = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="subscriptions")

# 3. Courses Table
class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_published = Column(Boolean, default=False, nullable=False)
    requires_subscription = Column(Boolean, default=False, nullable=False)
    required_telegram_channel = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    teacher = relationship("User", foreign_keys=[teacher_id])
    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    grades = relationship("Grade", back_populates="course", cascade="all, delete-orphan")

# 4. Enrollments Table
class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    status = Column(String(50), default="active", nullable=False)  # 'active', 'completed', 'dropped'

    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")

# 5. Lessons Table
class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    order_index = Column(Integer, default=1, nullable=False)
    content_text = Column(Text, nullable=False)
    is_preview = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    course = relationship("Course", back_populates="lessons")
    materials = relationship("LessonMaterial", back_populates="lesson", cascade="all, delete-orphan")
    progress_records = relationship("StudentProgress", back_populates="lesson", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="lesson")

# 6. Lesson Materials Table (PDFs, Docs)
class LessonMaterial(Base):
    __tablename__ = "lesson_materials"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    file_type = Column(String(50), default="pdf", nullable=False)
    file_path = Column(String(500), nullable=False)
    telegram_file_id = Column(String(255), nullable=True)
    file_size_bytes = Column(Integer, default=0, nullable=False)

    lesson = relationship("Lesson", back_populates="materials")

# 7. Student Progress Table
class StudentProgress(Base):
    __tablename__ = "student_progress"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    is_completed = Column(Boolean, default=True, nullable=False)
    completed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    student = relationship("User", back_populates="progress")
    lesson = relationship("Lesson", back_populates="progress_records")

# 8. Quizzes & Exams Table
class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=False)
    pass_percentage = Column(Float, default=70.0, nullable=False)
    time_limit_minutes = Column(Integer, nullable=True)
    is_exam = Column(Boolean, default=False, nullable=False)

    course = relationship("Course", back_populates="quizzes")
    lesson = relationship("Lesson", back_populates="quizzes")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")

# 9. Quiz Questions Table
class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    order_index = Column(Integer, default=1, nullable=False)
    points = Column(Integer, default=10, nullable=False)
    explanation = Column(Text, nullable=True)

    quiz = relationship("Quiz", back_populates="questions")
    answers = relationship("QuizAnswer", back_populates="question", cascade="all, delete-orphan")

# 10. Quiz Answers (Multiple Choice Options)
class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False)
    answer_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)

    question = relationship("QuizQuestion", back_populates="answers")

# 11. Quiz Attempts Table
class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    score_percentage = Column(Float, default=0.0, nullable=False)
    passed = Column(Boolean, default=False, nullable=False)
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    student = relationship("User", back_populates="quiz_attempts")
    quiz = relationship("Quiz", back_populates="attempts")

# 12. Grades Table
class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    final_score = Column(Float, default=0.0, nullable=False)
    grade_letter = Column(String(5), default="N/A", nullable=False)
    certificate_issued = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    student = relationship("User", back_populates="grades")
    course = relationship("Course", back_populates="grades")

# 13. Announcements Table
class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(200), nullable=False)
    message_text = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    author = relationship("User", foreign_keys=[author_id])
    course = relationship("Course", foreign_keys=[course_id])

    author = relationship("User", foreign_keys=[author_id])
    course = relationship("Course", foreign_keys=[course_id])
