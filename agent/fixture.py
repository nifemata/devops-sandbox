import subprocess
from datetime import datetime, timezone
from . import config
from .clients import Kube
from .gitrepo import push_tree
from .reset import _lab, reset

def fixture(learner, lab, name, do_reset=True):
    fdir = config.LABS_DIR / lab / "fixtures" / name
    if not fdir.is_dir():
        raise FileNotFoundError(f"no fixture {name} for lab {lab}")
    meta = _lab(lab); owner = meta.get("owner", learner).replace("<learner>", learner)
    ns = meta["namespace"].replace("<learner>", learner)
    out = {"learner": learner, "lab": lab, "fixture": name, "applied": {}}
    if do_reset:
        out["reset"] = reset(learner, lab, "all")["reset"]
    if (fdir / "repo").is_dir():
        out["applied"]["repo"] = push_tree(owner, meta["repo"], fdir / "repo", f"fixture: {name}", False, "fixture-bot")[:7]
    if (fdir / "k8s").is_dir():
        p = subprocess.run(["kubectl", "-n", ns, "apply", "-f", str(fdir / "k8s")], capture_output=True, text=True, env=Kube().env)
        out["applied"]["k8s"] = p.stdout.strip().splitlines() or p.stderr.strip()
    if (fdir / "apply.sh").is_file():
        p = subprocess.run(["bash", str(fdir / "apply.sh")], capture_output=True, text=True,
                           env=dict(Kube().env, LEARNER=learner, NAMESPACE=ns, OWNER=owner, REPO=meta["repo"]))
        out["applied"]["script"] = {"rc": p.returncode, "out": p.stdout[-500:], "err": p.stderr[-300:]}
    out["at"] = datetime.now(timezone.utc).isoformat()
    return out
