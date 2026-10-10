"""Thin clients for the three things the grader looks at: Gitea, Kubernetes, HTTP."""
import json
import os
import subprocess
import httpx
from . import config


class Gitea:
    def __init__(self):
        headers = {"Accept": "application/json"}
        auth = None
        if config.GITEA_TOKEN:
            headers["Authorization"] = f"token {config.GITEA_TOKEN}"
        else:
            auth = (config.GITEA_USER, config.GITEA_PASSWORD)
        self.c = httpx.Client(base_url=config.GITEA_URL + "/api/v1", headers=headers, auth=auth, timeout=10)

    def head_sha(self, owner: str, repo: str, branch: str = "main") -> str:
        r = self.c.get(f"/repos/{owner}/{repo}/branches/{branch}")
        r.raise_for_status()
        return r.json()["commit"]["id"]

    def latest_run(self, owner: str, repo: str, workflow: str | None = None, branch: str = "main") -> dict | None:
        """Newest Actions run on the branch. Gitea 1.24 exposes /actions/tasks (jobs); we take the newest."""
        r = self.c.get(f"/repos/{owner}/{repo}/actions/tasks", params={"limit": 20})
        r.raise_for_status()
        tasks = r.json().get("workflow_runs") or r.json().get("tasks") or []
        tasks = [t for t in tasks if t.get("head_branch", branch) == branch]
        if workflow:
            tasks = [t for t in tasks if t.get("workflow_id", "") in (workflow, "") or workflow in t.get("name", "")]
        if not tasks:
            return None
        tasks.sort(key=lambda t: t.get("run_number", t.get("id", 0)), reverse=True)
        return tasks[0]


class Kube:
    def __init__(self):
        self.env = dict(os.environ, KUBECONFIG=config.KUBECONFIG)

    def get(self, kind: str, name: str, namespace: str | None = None) -> dict | None:
        cmd = ["kubectl", "get", kind, name, "-o", "json"]
        if namespace:
            cmd += ["-n", namespace]
        p = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
        if p.returncode != 0:
            return None
        return json.loads(p.stdout)


def http_get(url: str) -> tuple[int, str]:
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True)
        return r.status_code, r.text
    except httpx.HTTPError as e:
        return 0, str(e)
