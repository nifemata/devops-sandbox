import subprocess, time
from datetime import datetime, timezone
import yaml
from . import config
from .clients import Kube
from .gitrepo import push_tree

def _lab(lab):
    return yaml.safe_load((config.LABS_DIR / lab / "lab.yaml").read_text())

def reset(learner, lab, scope="all"):
    if scope not in ("repo", "cluster", "all"):
        raise ValueError("scope must be repo, cluster or all")
    meta = _lab(lab); owner = meta.get("owner", learner).replace("<learner>", learner)
    t0 = time.time(); done = {}
    if scope in ("repo", "all"):
        template = config.LABS_DIR / lab / "template"
        done["repo"] = {"head": push_tree(owner, meta["repo"], template, f"reset: {lab} template", True, "devops-agent")[:7]}
    if scope in ("cluster", "all"):
        ns = meta["namespace"].replace("<learner>", learner)
        p = subprocess.run(["kubectl", "-n", ns, "delete", "deploy,svc,pod,job,cm,secret", "--all", "--ignore-not-found", "--wait=false"],
                           capture_output=True, text=True, env=Kube().env)
        done["cluster"] = {"namespace": ns, "deleted": p.stdout.strip().splitlines(), "err": p.stderr.strip() or None}
    return {"learner": learner, "lab": lab, "scope": scope, "reset": done,
            "seconds": round(time.time() - t0, 1), "at": datetime.now(timezone.utc).isoformat()}
