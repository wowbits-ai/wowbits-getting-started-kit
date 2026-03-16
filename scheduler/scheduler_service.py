"""
WowBits Agent Scheduler Service

A standalone FastAPI service that schedules agent executions using APScheduler.
When a scheduled job fires, it calls the ADK API to create a session and run
the agent with a predefined prompt.

Usage:
    cd wowbits-getting-started-kit/scheduler
    pip install -r requirements.txt
    python scheduler_service.py
"""

import json
import uuid
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("wowbits.scheduler")

ADK_API_URL = os.getenv("ADK_API_URL", "http://localhost:5152")
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SCHEDULES_FILE = DATA_DIR / "schedules.json"
HISTORY_FILE = DATA_DIR / "history.json"

scheduler = BackgroundScheduler(jobstores={"default": MemoryJobStore()})


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Starting WowBits Agent Scheduler...")
    for s in _load_schedules():
        if s.get("enabled", True):
            try:
                _sync_job(s)
            except Exception:
                logger.exception(f"Failed to restore schedule {s.get('id')}")
    scheduler.start()
    logger.info(f"Scheduler started with {len(scheduler.get_jobs())} active job(s)")
    yield
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


app = FastAPI(title="WowBits Agent Scheduler", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _read_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return default


def _write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, default=str))


def _load_schedules() -> list:
    return _read_json(SCHEDULES_FILE, [])


def _save_schedules(data: list):
    _write_json(SCHEDULES_FILE, data)


def _find_schedule(schedule_id: str) -> tuple[list, Optional[dict], int]:
    schedules = _load_schedules()
    for i, s in enumerate(schedules):
        if s.get("id") == schedule_id:
            return schedules, s, i
    return schedules, None, -1


def _load_history() -> list:
    return _read_json(HISTORY_FILE, [])


def _save_history(data: list):
    _write_json(HISTORY_FILE, data[-500:])


def _append_history(entry: dict):
    history = _load_history()
    history.append(entry)
    _save_history(history)


# ---------------------------------------------------------------------------
# Agent execution (called by APScheduler)
# ---------------------------------------------------------------------------

def execute_agent_job(schedule_id: str):
    """Called by APScheduler when a cron job fires."""
    schedules, schedule, idx = _find_schedule(schedule_id)
    if not schedule:
        logger.error(f"Schedule {schedule_id} not found")
        return

    agent_name = schedule["agent_name"]
    prompt = schedule.get("prompt", "run")
    adk_url = ADK_API_URL
    user_id = "anonymous"

    entry = {
        "id": str(uuid.uuid4()),
        "schedule_id": schedule_id,
        "agent_name": agent_name,
        "prompt": prompt,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "response_preview": None,
        "error": None,
    }

    logger.info(f"Executing scheduled job: agent={agent_name}, prompt={prompt[:80]}...")

    try:
        with httpx.Client(timeout=300) as client:
            session_url = f"{adk_url}/apps/{agent_name}/users/{user_id}/sessions"
            session_res = client.post(session_url, json={})
            session_res.raise_for_status()
            session_data = session_res.json()
            session_id = (
                session_data.get("id")
                or session_data.get("sessionId")
                or session_data.get("session_id")
            )
            if not session_id:
                raise ValueError("ADK did not return a session ID")

            logger.info(f"Created session {session_id} for {agent_name}")

            run_url = f"{adk_url}/run"
            run_payload = {
                "appName": agent_name,
                "userId": user_id,
                "sessionId": session_id,
                "streaming": False,
                "newMessage": {
                    "role": "user",
                    "parts": [{"text": prompt}],
                },
            }
            run_res = client.post(run_url, json=run_payload)
            run_res.raise_for_status()

            response_text = run_res.text
            try:
                parsed = json.loads(response_text)
                texts = []
                events = parsed if isinstance(parsed, list) else [parsed]
                for evt in events:
                    parts = (evt.get("content") or {}).get("parts") or evt.get("parts") or []
                    for p in parts:
                        if isinstance(p, dict) and p.get("text"):
                            texts.append(p["text"])
                if texts:
                    response_text = "\n".join(texts)
            except (json.JSONDecodeError, AttributeError):
                pass

            entry["status"] = "success"
            entry["response_preview"] = response_text[:2000]
            entry["session_id"] = session_id
            logger.info(f"Job completed: agent={agent_name}, session={session_id}")

    except Exception as e:
        entry["status"] = "error"
        entry["error"] = str(e)
        logger.exception(f"Job failed: agent={agent_name}")

    entry["finished_at"] = datetime.now(timezone.utc).isoformat()

    schedules, schedule, idx = _find_schedule(schedule_id)
    if schedule:
        schedule["last_run"] = entry["finished_at"]
        schedule["last_status"] = entry["status"]
        _save_schedules(schedules)

    _append_history(entry)


# ---------------------------------------------------------------------------
# Pydantic models (matching frontend expectations)
# ---------------------------------------------------------------------------

class ScheduleCreate(BaseModel):
    agent_name: str
    cron: str
    prompt: str = "run"
    timezone: str = "Asia/Kolkata"
    enabled: bool = True
    label: Optional[str] = None


class ScheduleUpdate(BaseModel):
    agent_name: Optional[str] = None
    cron: Optional[str] = None
    prompt: Optional[str] = None
    timezone: Optional[str] = None
    enabled: Optional[bool] = None
    label: Optional[str] = None


# ---------------------------------------------------------------------------
# APScheduler helpers
# ---------------------------------------------------------------------------

def _parse_cron(cron_str: str, tz: str = "UTC") -> Optional[CronTrigger]:
    """Parse a 5-field cron expression into an APScheduler CronTrigger."""
    parts = cron_str.strip().split()
    if len(parts) != 5:
        return None
    try:
        return CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            timezone=tz,
        )
    except Exception:
        logger.exception(f"Invalid cron expression: {cron_str}")
        return None


def _sync_job(schedule: dict):
    """Add or replace an APScheduler job for this schedule."""
    job_id = f"sched_{schedule['id']}"
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)

    if not schedule.get("enabled", True):
        return

    trigger = _parse_cron(schedule["cron"], schedule.get("timezone", "UTC"))
    if not trigger:
        logger.error(f"Cannot schedule {schedule['id']}: bad cron '{schedule['cron']}'")
        return

    scheduler.add_job(
        execute_agent_job,
        trigger=trigger,
        args=[schedule["id"]],
        id=job_id,
        name=f"{schedule['agent_name']} – {schedule['cron']}",
        replace_existing=True,
    )
    logger.info(f"Scheduled {job_id}: {schedule['agent_name']} @ {schedule['cron']} ({schedule.get('timezone', 'UTC')})")


def _remove_job(schedule_id: str):
    job_id = f"sched_{schedule_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


def _get_next_run(schedule_id: str) -> Optional[str]:
    job = scheduler.get_job(f"sched_{schedule_id}")
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "scheduler_running": scheduler.running,
        "active_jobs": len(scheduler.get_jobs()),
        "adk_url": ADK_API_URL,
    }


@app.get("/schedules")
def list_schedules():
    schedules = _load_schedules()
    for s in schedules:
        s["next_run"] = _get_next_run(s["id"])
    return schedules


@app.get("/schedules/history")
def get_history(limit: int = Query(50, ge=1, le=500)):
    history = _load_history()
    return history[-limit:]


@app.get("/schedules/{schedule_id}")
def get_schedule(schedule_id: str):
    _, schedule, _ = _find_schedule(schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    schedule["next_run"] = _get_next_run(schedule_id)
    return schedule


@app.post("/schedules")
def create_schedule(body: ScheduleCreate):
    trigger = _parse_cron(body.cron, body.timezone)
    if not trigger:
        raise HTTPException(400, f"Invalid cron expression: {body.cron}")

    sid = str(uuid.uuid4())[:8]
    schedule = {
        "id": sid,
        "agent_name": body.agent_name,
        "cron": body.cron,
        "prompt": body.prompt,
        "timezone": body.timezone,
        "enabled": body.enabled,
        "label": body.label,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_run": None,
        "last_status": None,
    }

    schedules = _load_schedules()
    schedules.append(schedule)
    _save_schedules(schedules)

    _sync_job(schedule)
    schedule["next_run"] = _get_next_run(sid)
    return schedule


@app.put("/schedules/{schedule_id}")
def update_schedule(schedule_id: str, body: ScheduleUpdate):
    schedules, schedule, idx = _find_schedule(schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    if body.agent_name is not None:
        schedule["agent_name"] = body.agent_name
    if body.cron is not None:
        trigger = _parse_cron(body.cron, body.timezone or schedule.get("timezone", "UTC"))
        if not trigger:
            raise HTTPException(400, f"Invalid cron expression: {body.cron}")
        schedule["cron"] = body.cron
    if body.prompt is not None:
        schedule["prompt"] = body.prompt
    if body.timezone is not None:
        schedule["timezone"] = body.timezone
    if body.enabled is not None:
        schedule["enabled"] = body.enabled
    if body.label is not None:
        schedule["label"] = body.label

    schedules[idx] = schedule
    _save_schedules(schedules)

    _remove_job(schedule_id)
    _sync_job(schedule)
    schedule["next_run"] = _get_next_run(schedule_id)
    return schedule


@app.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: str):
    schedules, schedule, idx = _find_schedule(schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    _remove_job(schedule_id)
    schedules.pop(idx)
    _save_schedules(schedules)
    return {"deleted": schedule_id}


@app.post("/schedules/{schedule_id}/trigger")
def trigger_now(schedule_id: str):
    """Manually trigger a scheduled job immediately (for testing)."""
    _, schedule, _ = _find_schedule(schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    execute_agent_job(schedule_id)
    return {"triggered": schedule_id, "status": "done"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("SCHEDULER_PORT", "5153"))
    logger.info(f"Starting scheduler on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
