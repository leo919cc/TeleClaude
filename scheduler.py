"""Scheduled prompts — cron-based recurring Claude runs."""

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

JOBS_FILE = Path(__file__).resolve().parent / "scheduled_jobs.json"

# Offset so scheduled runs get their own session, not the user's active one
_SCHED_UID_OFFSET = 1_000_000_000


@dataclass
class ScheduledJob:
    id: str
    cron: str
    prompt: str
    chat_id: int
    user_id: int
    project_dir: str | None = None
    created_at: str = ""


class Scheduler:
    def __init__(self, runner, bot):
        self.runner = runner
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.jobs: dict[str, ScheduledJob] = {}

    def start(self):
        self._load()
        for job in self.jobs.values():
            try:
                self._register(job)
            except Exception:
                logger.warning("Skipping invalid job %s: %s", job.id, job.cron)
        self.scheduler.start()
        logger.info("Scheduler started with %d jobs", len(self.jobs))

    def add(self, cron: str, prompt: str, chat_id: int, user_id: int,
            project_dir: str | None) -> ScheduledJob:
        job = ScheduledJob(
            id=uuid.uuid4().hex[:8],
            cron=cron,
            prompt=prompt,
            chat_id=chat_id,
            user_id=user_id,
            project_dir=project_dir,
            created_at=datetime.now().isoformat(),
        )
        self._register(job)  # Validates cron — raises on bad expression
        self.jobs[job.id] = job
        self._save()
        return job

    def remove(self, job_id: str) -> bool:
        if job_id not in self.jobs:
            return False
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass
        del self.jobs[job_id]
        self._save()
        return True

    def list_jobs(self, user_id: int) -> list[ScheduledJob]:
        return [j for j in self.jobs.values() if j.user_id == user_id]

    def _register(self, job: ScheduledJob):
        parts = job.cron.split()
        trigger = CronTrigger(
            minute=parts[0], hour=parts[1], day=parts[2],
            month=parts[3], day_of_week=parts[4],
        )
        self.scheduler.add_job(
            self._execute, trigger, id=job.id,
            args=[job], replace_existing=True,
        )

    async def _execute(self, job: ScheduledJob):
        try:
            sched_uid = job.user_id + _SCHED_UID_OFFSET
            if job.project_dir:
                self.runner.set_project(sched_uid, Path(job.project_dir))

            result = await self.runner.run(sched_uid, job.prompt)

            # Clean up temporary session
            self.runner.sessions.pop(sched_uid, None)

            text = result.text
            if len(text) > 4000:
                text = text[:4000] + "\n... (truncated)"

            await self.bot.send_message(
                job.chat_id,
                f"[scheduled] {job.prompt[:50]}\n\n{text}",
            )
        except Exception:
            logger.exception("Scheduled job %s failed", job.id)

    def _load(self):
        if not JOBS_FILE.exists():
            return
        try:
            data = json.loads(JOBS_FILE.read_text())
            for item in data:
                job = ScheduledJob(**item)
                self.jobs[job.id] = job
        except Exception:
            logger.exception("Failed to load scheduled jobs")

    def _save(self):
        data = [asdict(j) for j in self.jobs.values()]
        JOBS_FILE.write_text(json.dumps(data, indent=2))
