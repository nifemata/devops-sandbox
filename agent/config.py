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
# What learners click: the public address when Gitea is published (reuses GITEA_ROOT_URL from .env); else GITEA_URL.
GITEA_PUBLIC_URL = (os.environ.get("GITEA_PUBLIC_URL") or os.environ.get("GITEA_ROOT_URL") or GITEA_URL).rstrip("/")
GITEA_USER = os.environ.get("GITEA_USER", "instructor")
GITEA_PASSWORD = os.environ.get("GITEA_PASSWORD", "")
GITEA_TOKEN = os.environ.get("GITEA_TOKEN", "")          # preferred over password if set
KUBECONFIG = os.environ.get("KUBECONFIG", str(ROOT / "kubeconfig.yaml"))
AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "dev-token")  # static bearer: CLI / break-glass (acts as instructor)
# Keycloak (phase 3). Empty issuer = Keycloak off, static token only (laptop sandbox).
KEYCLOAK_ISSUER = os.environ.get("KEYCLOAK_ISSUER", "").rstrip("/")          # e.g. https://devops-auth.mubita.digital/realms/workshop
KEYCLOAK_JWKS_URL = os.environ.get("KEYCLOAK_JWKS_URL") or (KEYCLOAK_ISSUER + "/protocol/openid-connect/certs" if KEYCLOAK_ISSUER else "")
KEYCLOAK_AUDIENCE = os.environ.get("KEYCLOAK_AUDIENCE", "devops-agent")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "").rstrip("/")   # e.g. https://devops-apps.mubita.digital; empty = no ingress (laptop)
LABS_DIR = Path(os.environ.get("LABS_DIR", ROOT / "labs"))
STATE_DIR = Path(os.environ.get("STATE_DIR", ROOT / "agent" / "state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)
