"""
INDAGO Evidence Capture Platform
Scheduler Tasks - Periodic Evidence Captures
"""
from datetime import datetime, timezone
from croniter import croniter
from sqlalchemy import select
import logging

from app.tasks.celery_app import celery_app
from app.tasks.capture_tasks import run_async
from app.core.database import AsyncSessionLocal
from app.models.capture import ScheduledCapture, EvidenceCapture, CaptureStatus

logger = logging.getLogger(__name__)


@celery_app.task(name="scheduler.run_due_captures")
def run_due_captures():
    """Check and execute due scheduled captures."""
    return run_async(_run_due_captures_async())


async def _run_due_captures_async():
    """Execute all scheduled captures that are due."""
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(ScheduledCapture).where(
                ScheduledCapture.is_active == True,
                ScheduledCapture.next_run_at <= now,
            )
        )
        scheduled = result.scalars().all()

        executed = 0
        for sched in scheduled:
            try:
                # Create new capture
                new_capture = EvidenceCapture(
                    url=sched.url,
                    capture_type=sched.capture_type,
                    investigator_id=sched.investigator_id,
                    case_number=sched.case_number,
                    status=CaptureStatus.PENDING,
                    capture_options=sched.capture_options,
                )
                db.add(new_capture)
                await db.flush()

                # Queue task
                from app.tasks.capture_tasks import execute_forensic_capture
                task = execute_forensic_capture.delay(new_capture.id)
                new_capture.celery_task_id = task.id

                # Update schedule
                cron = croniter(sched.schedule_cron, now)
                sched.next_run_at = cron.get_next(datetime)
                sched.last_run_at = now
                sched.run_count += 1

                executed += 1
            except Exception as e:
                logger.error(f"Failed to execute scheduled capture {sched.id}: {e}")

        await db.commit()
        return {"executed": executed, "checked": len(scheduled)}
