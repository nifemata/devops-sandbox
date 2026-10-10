"""devops-agent v0.1 — phase 2, step 2: grade is live; the other verbs are stubs that say so."""
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from . import config
from .grade import grade
from .clients import Gitea, Kube, http_get

app = FastAPI(title="devops-agent", version="0.1.0")


def _auth(authorization: str | None):
    if authorization != f"Bearer {config.AGENT_TOKEN}":
        raise HTTPException(401, {"error": "unauthorized", "detail": "bad or missing bearer token"})


def _not_yet(verb: str):
    return JSONResponse({"error": "not_implemented", "detail": f"{verb} arrives at build-plan step 3–4"}, status_code=501)


@app.get("/healthz")
def healthz():
    out = {}
    try:
        Gitea().c.get("/version").raise_for_status(); out["gitea"] = "ok"
    except Exception as e:  # noqa: BLE001
        out["gitea"] = str(e)
    out["k3s"] = "ok" if Kube().get("node", "", None) is not None or Kube().get("namespace", "kube-system") else "unreachable"
    return out


@app.post("/v1/envs/{learner}/{lab}/grade")
def grade_env(learner: str, lab: str, authorization: str | None = Header(default=None)):
    _auth(authorization)
    if not (config.LABS_DIR / lab / "grade.yaml").exists():
        raise HTTPException(404, {"error": "not_found", "detail": f"no grade.yaml for lab {lab}"})
    return grade(learner, lab)


@app.get("/v1/envs/{learner}/{lab}")
def status(learner: str, lab: str, authorization: str | None = Header(default=None)):
    _auth(authorization)
    f = config.STATE_DIR / f"{learner}.{lab}.grade.json"
    if not f.exists():
        raise HTTPException(404, {"error": "not_found", "detail": "no environment record yet"})
    return {"learner": learner, "lab": lab, "state": "ready", "last_grade": f.read_text() and __import__("json").loads(f.read_text())}


@app.post("/v1/envs")
def provision(authorization: str | None = Header(default=None)):
    _auth(authorization); return _not_yet("provision")


@app.post("/v1/envs/{learner}/{lab}/reset")
def reset(learner: str, lab: str, authorization: str | None = Header(default=None)):
    _auth(authorization); return _not_yet("reset")


@app.post("/v1/envs/{learner}/{lab}/fixtures/{name}")
def fixture(learner: str, lab: str, name: str, authorization: str | None = Header(default=None)):
    _auth(authorization); return _not_yet("fixture")
