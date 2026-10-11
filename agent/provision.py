"""provision: give a learner a working, isolated environment for a lab. Idempotent: every step checks first.
deprovision: remove exactly what provision created."""
import json, shutil, subprocess, tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import httpx, yaml
from . import config
from .clients import Gitea, Kube
from .gitrepo import push_tree, _auth_url, _run, _copy_tree
from .jobs import step
from .reset import _lab


def _record_path(learner, lab):
    return config.STATE_DIR / f"{learner}.{lab}.env.json"


def read_record(learner, lab):
    f = _record_path(learner, lab)
    return json.loads(f.read_text()) if f.exists() else None


def _ensure_org(g: Gitea, owner):
    if g.c.get(f"/orgs/{owner}").status_code == 200 or g.c.get(f"/users/{owner}").status_code == 200:
        return "exists"
    r = g.c.post("/orgs", json={"username": owner, "visibility": "private"})
    r.raise_for_status(); return "created"


def _ensure_repo(g: Gitea, owner, repo):
    if g.c.get(f"/repos/{owner}/{repo}").status_code == 200:
        return "exists"
    body = {"name": repo, "private": False, "default_branch": "main", "auto_init": False}
    r = g.c.post(f"/orgs/{owner}/repos", json=body)
    if r.status_code == 404:  # owner is a user, not an org
        r = g.c.post("/user/repos", json=body)
    r.raise_for_status(); return "created"


def _enable_actions(g: Gitea, owner, repo):
    g.c.patch(f"/repos/{owner}/{repo}", json={"has_actions": True}).raise_for_status()


def _repo_is_empty(g: Gitea, owner, repo):
    return bool(g.c.get(f"/repos/{owner}/{repo}").json().get("empty"))


def _seed_empty_repo(owner, repo, template: Path):
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"; work.mkdir()
        _run(["git", "init", "-q", "-b", "main"], work)
        _copy_tree(template, work)
        _run(["git", "add", "-A"], work)
        _run(["git", "-c", "user.name=devops-agent", "-c", "user.email=devops-agent@local", "commit", "-q", "-m", "provision: lab template"], work)
        _run(["git", "push", "-q", _auth_url(owner, repo), "main"], work)
        return _run(["git", "rev-parse", "HEAD"], work)


def _put_secret(g: Gitea, owner, repo, name, value):
    g.c.put(f"/repos/{owner}/{repo}/actions/secrets/{name}", json={"data": value}).raise_for_status()


def _ensure_namespace(ns, quota: dict | None, isolate: bool):
    env = Kube().env
    manifests = [{"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": ns, "labels": {"devops-lab/managed": "true"}}}]
    if quota:
        manifests.append({"apiVersion": "v1", "kind": "ResourceQuota", "metadata": {"name": "learner", "namespace": ns},
                          "spec": {"hard": quota}})
        manifests.append({"apiVersion": "v1", "kind": "LimitRange", "metadata": {"name": "defaults", "namespace": ns},
                          "spec": {"limits": [{"type": "Container",
                                               "default": {"cpu": "250m", "memory": "128Mi"},
                                               "defaultRequest": {"cpu": "50m", "memory": "64Mi"}}]}})
    if isolate:
        manifests.append({"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
                          "metadata": {"name": "default-deny-cross-namespace", "namespace": ns},
                          "spec": {"podSelector": {}, "policyTypes": ["Ingress"],
                                   "ingress": [{"from": [{"podSelector": {}}]}, {}]}})
    doc = "\n---\n".join(yaml.safe_dump(m) for m in manifests)
    p = subprocess.run(["kubectl", "apply", "-f", "-"], input=doc, capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip()[:300])
    return p.stdout.strip().splitlines()


def _ensure_ingress(ns, learner, service="hello", port=80):
    """Traefik Ingress so the learner's app is reachable at APP_BASE_URL/<learner>/ (prefix stripped)."""
    env = Kube().env
    manifests = [
        {"apiVersion": "traefik.io/v1alpha1", "kind": "Middleware",
         "metadata": {"name": "strip-prefix", "namespace": ns},
         "spec": {"stripPrefix": {"prefixes": [f"/{learner}"]}}},
        {"apiVersion": "networking.k8s.io/v1", "kind": "Ingress",
         "metadata": {"name": service, "namespace": ns,
                      "annotations": {"traefik.ingress.kubernetes.io/router.middlewares": f"{ns}-strip-prefix@kubernetescrd"}},
         "spec": {"rules": [{"http": {"paths": [
             {"path": f"/{learner}", "pathType": "Prefix",
              "backend": {"service": {"name": service, "port": {"number": port}}}}]}}]}},
    ]
    doc = "\n---\n".join(yaml.safe_dump(m) for m in manifests)
    p = subprocess.run(["kubectl", "apply", "-f", "-"], input=doc, capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip()[:300])
    return p.stdout.strip().splitlines()


def provision(job, learner: str, lab: str) -> dict:
    meta = _lab(lab)
    owner = meta.get("owner", "<learner>").replace("<learner>", learner)
    repo = meta["repo"]
    ns = meta["namespace"].replace("<learner>", learner)
    g = Gitea()

    step(job, f"gitea: org/user {owner} {_ensure_org(g, owner)}")
    step(job, f"gitea: repo {owner}/{repo} {_ensure_repo(g, owner, repo)}")
    _enable_actions(g, owner, repo); step(job, "gitea: actions enabled")

    template = config.LABS_DIR / lab / meta.get("template", "template")
    if _repo_is_empty(g, owner, repo):
        head = _seed_empty_repo(owner, repo, template); step(job, f"gitea: seeded template, head {head[:7]}")
    else:
        head = g.head_sha(owner, repo); step(job, f"gitea: repo already has history, head {head[:7]} (use reset to re-seed)")

    reg_user = config.GITEA_USER
    reg_token = config.GITEA_TOKEN or config.GITEA_PASSWORD
    _put_secret(g, owner, repo, "REGISTRY_USER", reg_user)
    _put_secret(g, owner, repo, "REGISTRY_TOKEN", reg_token)
    step(job, "gitea: pipeline secrets set")

    quota = meta.get("quota", {"cpu": "1", "memory": "2Gi", "pods": "10"})
    out = _ensure_namespace(ns, quota, bool(meta.get("isolate", False)))
    step(job, f"k3s: namespace {ns}: " + "; ".join(out))

    app_url = meta.get("app_url") or ""
    if config.APP_BASE_URL and meta.get("app_url", None) == "":
        out = _ensure_ingress(ns, learner)
        app_url = f"{config.APP_BASE_URL}/{learner}/"
        step(job, f"k3s: ingress {app_url}: " + "; ".join(out))

    base = config.GITEA_PUBLIC_URL
    record = {"learner": learner, "lab": lab, "state": "ready",
              "owner": owner, "repo": repo, "namespace": ns, "head": head[:7],
              "urls": {"gitea": f"{base}/{owner}/{repo}", "actions": f"{base}/{owner}/{repo}/actions",
                       "app": app_url or meta.get("app_url", "http://localhost:30080")},
              "provisioned_at": datetime.now(timezone.utc).isoformat(),
              "expires_at": (datetime.now(timezone.utc) + timedelta(days=int(meta.get("ttl_days", 30)))).isoformat()}
    _record_path(learner, lab).write_text(json.dumps(record, indent=2))
    step(job, "env record written")
    return record


def deprovision(job, learner: str, lab: str) -> dict:
    meta = _lab(lab)
    owner = meta.get("owner", "<learner>").replace("<learner>", learner)
    ns = meta["namespace"].replace("<learner>", learner)
    g = Gitea()
    done = {}
    if meta.get("protected"):
        raise RuntimeError(f"lab {lab} is marked protected in lab.yaml; deprovision refused")
    r = g.c.delete(f"/repos/{owner}/{meta['repo']}")
    done["repo"] = r.status_code; step(job, f"gitea: repo delete -> {r.status_code}")
    if owner != config.GITEA_USER and g.c.get(f"/orgs/{owner}").status_code == 200:
        r = g.c.delete(f"/orgs/{owner}"); done["org"] = r.status_code; step(job, f"gitea: org delete -> {r.status_code}")
    p = subprocess.run(["kubectl", "delete", "namespace", ns, "--ignore-not-found", "--wait=false"],
                       capture_output=True, text=True, env=Kube().env)
    done["namespace"] = p.stdout.strip() or p.stderr.strip(); step(job, f"k3s: {done['namespace']}")
    f = _record_path(learner, lab)
    if f.exists():
        f.unlink()
    return done
