"""All settings come from the environment; .env in the sandbox root is loaded if present."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_env = ROOT / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

GITEA_URL = os.environ.get("GITEA_URL", "http://gitea:3000").rstrip("/")
GITEA_USER = os.environ.get("GITEA_USER", "instructor")
GITEA_PASSWORD = os.environ.get("GITEA_PASSWORD", "")
GITEA_TOKEN = os.environ.get("GITEA_TOKEN", "")          # preferred over password if set
KUBECONFIG = os.environ.get("KUBECONFIG", str(ROOT / "kubeconfig.yaml"))
AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "dev-token")  # bearer the Workshop presents
LABS_DIR = Path(os.environ.get("LABS_DIR", ROOT / "labs"))
STATE_DIR = Path(os.environ.get("STATE_DIR", ROOT / "agent" / "state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)
