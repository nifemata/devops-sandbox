"""devops-agent v0.4 — phase 3: Keycloak sign-in (learners act on themselves, instructors on anyone; static token = CLI)."""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from . import config
from .grade import grade
from .reset import reset as do_reset
from .fixture import fixture as do_fixture
from . import jobs
from .provision import provision as do_provision, deprovision as do_deprovision, read_record
from pydantic import BaseModel
from .clients import Gitea, Kube, http_get
from .auth import Principal, current_user, require

from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="devops-agent", version="0.4.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


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
    out["auth"] = "keycloak+static" if config.KEYCLOAK_ISSUER else "static"
    return out


@app.get("/v1/me")
def me(who: Principal = Depends(current_user)):
    """Who the agent thinks you are — the tile uses this after sign-in."""
    return {"learner": who.name, "roles": sorted(who.roles), "instructor": who.instructor, "static": who.static}


@app.post("/v1/envs/{learner}/{lab}/grade")
def grade_env(learner: str, lab: str, who: Principal = Depends(current_user)):
    require(who, learner)
    if not (config.LABS_DIR / lab / "grade.yaml").exists():
        raise HTTPException(404, {"error": "not_found", "detail": f"no grade.yaml for lab {lab}"})
    return grade(learner, lab)


@app.get("/v1/envs/{learner}/{lab}")
def status(learner: str, lab: str, who: Principal = Depends(current_user)):
    require(who, learner)
    rec = read_record(learner, lab)
    if rec is None:
        raise HTTPException(404, {"error": "not_found", "detail": "no environment; POST /v1/envs to provision"})
    f = config.STATE_DIR / f"{learner}.{lab}.grade.json"
    if f.exists():
        import json
        g = json.loads(f.read_text()); rec["last_grade"] = {"score": g["score"], "of": g["of"], "at": g["graded_at"]}
    return rec

class ProvisionRequest(BaseModel):
    learner: str
    lab: str


@app.post("/v1/envs", status_code=202)
def provision(req: ProvisionRequest, who: Principal = Depends(current_user)):
    require(who, req.learner)
    if not (config.LABS_DIR / req.lab / "lab.yaml").exists():
        raise HTTPException(404, {"error": "not_found", "detail": f"no lab.yaml for lab {req.lab}"})
    job = jobs.start("provision", do_provision, req.learner, req.lab)
    return {"job": job["id"], "state": job["state"], "poll": f"/v1/jobs/{job['id']}"}


@app.delete("/v1/envs/{learner}/{lab}", status_code=202)
def deprovision(learner: str, lab: str, who: Principal = Depends(current_user)):
    require(who, learner)
    job = jobs.start("deprovision", do_deprovision, learner, lab)
    return {"job": job["id"], "state": job["state"], "poll": f"/v1/jobs/{job['id']}"}


@app.get("/v1/jobs/{job_id}")
def job_status(job_id: str, who: Principal = Depends(current_user)):
    j = jobs.get(job_id)
    if j is None:
        raise HTTPException(404, {"error": "not_found", "detail": "no such job"})
    if j.get("learner"):
        require(who, j["learner"])
    return j


@app.post("/v1/envs/{learner}/{lab}/reset")
def reset(learner: str, lab: str, scope: str = "all", who: Principal = Depends(current_user)):
    require(who, learner)
    try:
        return do_reset(learner, lab, scope)
    except ValueError as e:
        raise HTTPException(400, {"error": "bad_request", "detail": str(e)})
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, {"error": "upstream", "detail": str(e)})


@app.post("/v1/envs/{learner}/{lab}/fixtures/{name}")
def fixture(learner: str, lab: str, name: str, reset: bool = True, who: Principal = Depends(current_user)):
    require(who, learner)
    try:
        return do_fixture(learner, lab, name, do_reset=reset)
    except FileNotFoundError as e:
        raise HTTPException(404, {"error": "not_found", "detail": str(e)})
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, {"error": "upstream", "detail": str(e)})
