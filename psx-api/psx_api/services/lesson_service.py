"""Lesson + skill-tree service (Phase 4 Step 66)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.learning.curriculum import (
    CURRICULUM,
    grade_attempt,
    quiz_to_jsonable,
)
from psx_api.models.community import Lesson, UserLessonProgress


class LessonService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def seed_curriculum(self) -> int:
        """
        Idempotent upsert from psx_api.learning.curriculum into the lessons
        table. Called from a startup hook or admin endpoint. Returns the
        count of lessons inserted (existing ones are left untouched —
        admins can edit content directly in DB later).
        """
        existing = (await self._db.execute(select(Lesson.slug))).scalars().all()
        existing_set = set(existing)
        inserted = 0
        for i, lc in enumerate(CURRICULUM):
            if lc.slug in existing_set:
                continue
            self._db.add(
                Lesson(
                    slug=lc.slug,
                    title=lc.title,
                    category=lc.category,
                    difficulty=lc.difficulty,
                    body_md=lc.body_md,
                    quiz=quiz_to_jsonable(lc.quiz),
                    display_order=i,
                )
            )
            inserted += 1
        await self._db.flush()
        return inserted

    async def list_with_progress(self, user_id: str) -> list[dict[str, Any]]:
        rows = (
            await self._db.execute(
                select(
                    Lesson.id,
                    Lesson.slug,
                    Lesson.title,
                    Lesson.category,
                    Lesson.difficulty,
                    UserLessonProgress.started_at,
                    UserLessonProgress.completed_at,
                    UserLessonProgress.quiz_score,
                )
                .outerjoin(
                    UserLessonProgress,
                    (UserLessonProgress.lesson_id == Lesson.id)
                    & (UserLessonProgress.user_id == user_id),
                )
                .order_by(Lesson.display_order, Lesson.id)
            )
        ).all()
        return [
            {
                "id": r[0],
                "slug": r[1],
                "title": r[2],
                "category": r[3],
                "difficulty": r[4],
                "started": r[5] is not None,
                "completed": r[6] is not None,
                "quiz_score": r[7],
            }
            for r in rows
        ]

    async def get_with_progress(self, user_id: str, slug: str) -> dict[str, Any] | None:
        lesson = (
            await self._db.execute(select(Lesson).where(Lesson.slug == slug))
        ).scalar_one_or_none()
        if not lesson:
            return None

        # Mark as started (or update last_seen_at)
        progress = (
            await self._db.execute(
                select(UserLessonProgress).where(
                    UserLessonProgress.user_id == user_id,
                    UserLessonProgress.lesson_id == lesson.id,
                )
            )
        ).scalar_one_or_none()
        now = datetime.now(UTC)
        if progress is None:
            progress = UserLessonProgress(
                user_id=user_id,
                lesson_id=lesson.id,
                started_at=now,
                last_seen_at=now,
            )
            self._db.add(progress)
            try:
                await self._db.flush()
            except IntegrityError:
                await self._db.rollback()
        else:
            progress.last_seen_at = now
            await self._db.flush()

        # Strip `correct` flag from quiz options before returning to client
        # so the answer key isn't leaked.
        scrubbed_quiz = [
            {
                "question": q["question"],
                "options": [{"text": o["text"]} for o in q["options"]],
            }
            for q in lesson.quiz
        ]

        return {
            "id": lesson.id,
            "slug": lesson.slug,
            "title": lesson.title,
            "category": lesson.category,
            "difficulty": lesson.difficulty,
            "body_md": lesson.body_md,
            "quiz": scrubbed_quiz,
            "progress": {
                "started_at": progress.started_at.isoformat() if progress.started_at else None,
                "completed_at": progress.completed_at.isoformat()
                if progress.completed_at
                else None,
                "quiz_score": progress.quiz_score,
            },
        }

    async def submit_quiz(self, user_id: str, slug: str, answers: list[int]) -> dict[str, Any]:
        lesson = (
            await self._db.execute(select(Lesson).where(Lesson.slug == slug))
        ).scalar_one_or_none()
        if not lesson:
            return {"error": "Lesson not found", "score": 0}

        score = grade_attempt(lesson.quiz, answers)
        completed = score >= 70  # 70%+ counts as passing

        progress = (
            await self._db.execute(
                select(UserLessonProgress).where(
                    UserLessonProgress.user_id == user_id,
                    UserLessonProgress.lesson_id == lesson.id,
                )
            )
        ).scalar_one_or_none()
        now = datetime.now(UTC)
        if progress is None:
            progress = UserLessonProgress(
                user_id=user_id,
                lesson_id=lesson.id,
                started_at=now,
                quiz_score=score,
                completed_at=now if completed else None,
                last_seen_at=now,
            )
            self._db.add(progress)
        else:
            # Keep highest score
            if progress.quiz_score is None or score > progress.quiz_score:
                progress.quiz_score = score
            if completed and not progress.completed_at:
                progress.completed_at = now
            progress.last_seen_at = now
        await self._db.flush()

        # Reveal correct indices so the UI can show feedback
        correct_indices = []
        for q in lesson.quiz:
            for idx, opt in enumerate(q.get("options", [])):
                if opt.get("correct"):
                    correct_indices.append(idx)
                    break

        return {
            "score": score,
            "completed": completed,
            "correct_indices": correct_indices,
        }
