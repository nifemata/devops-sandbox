import shutil, subprocess, tempfile
from pathlib import Path
from urllib.parse import quote
from . import config
IGNORE = {".git", "__pycache__", ".pytest_cache", ".venv"}

def _auth_url(owner, repo):
    user = quote(config.GITEA_USER, safe=""); secret = quote(config.GITEA_TOKEN or config.GITEA_PASSWORD, safe="")
    host = config.GITEA_URL.split("://", 1)[1]
    return f"http://{user}:{secret}@{host}/{owner}/{repo}.git"

def _run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}: {p.stderr.strip()[:300]}")
    return p.stdout.strip()

def _copy_tree(src, dst):
    for item in src.iterdir():
        if item.name in IGNORE: continue
        target = dst / item.name
        if item.is_dir(): shutil.copytree(item, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*IGNORE))
        else: shutil.copy2(item, target)

def push_tree(owner, repo, src, message, replace, author, branch="main"):
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        _run(["git", "clone", "--quiet", "--branch", branch, _auth_url(owner, repo), str(work)], tmp)
        if replace:
            for item in work.iterdir():
                if item.name == ".git": continue
                shutil.rmtree(item) if item.is_dir() else item.unlink()
        _copy_tree(src, work)
        _run(["git", "add", "-A"], work)
        if not _run(["git", "status", "--porcelain"], work):
            return _run(["git", "rev-parse", "HEAD"], work)
        _run(["git", "-c", f"user.name={author}", "-c", f"user.email={author}@devops-agent", "commit", "-q", "-m", message], work)
        _run(["git", "push", "-q", "origin", branch], work)
        return _run(["git", "rev-parse", "HEAD"], work)
