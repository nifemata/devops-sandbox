"""Background jobs for the slow verbs (provision, deprovision). In-memory + one JSON file per job."""
import json, threading, traceback, uuid
from datetime import datetime, timezone
from . import config

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def _save(job):
    (config.STATE_DIR / f"job.{job['id']}.json").write_text(json.dumps(job, indent=2, default=str))


def start(kind: str, fn, *args) -> dict:
    job = {"id": uuid.uuid4().hex[:12], "kind": kind, "state": "queued", "steps": [],
           "learner": args[0] if args else None,
           "created_at": datetime.now(timezone.utc).isoformat(), "result": None, "error": None}
    with _lock:
        _jobs[job["id"]] = job
    _save(job)

    def run():
        job["state"] = "running"; _save(job)
        try:
            job["result"] = fn(job, *args)
            job["state"] = "done"
        except Exception as e:  # noqa: BLE001
            job["state"] = "failed"; job["error"] = f"{e}"; job["trace"] = traceback.format_exc()[-800:]
        job["finished_at"] = datetime.now(timezone.utc).isoformat(); _save(job)

    threading.Thread(target=run, daemon=True).start()
    return job


def get(job_id: str) -> dict | None:
    with _lock:
        j = _jobs.get(job_id)
    if j is None:
        f = config.STATE_DIR / f"job.{job_id}.json"
        if f.exists():
            j = json.loads(f.read_text())
    return j


def step(job, text):
    job["steps"].append({"at": datetime.now(timezone.utc).isoformat(), "msg": text}); _save(job)
