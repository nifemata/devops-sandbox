"""Who is calling? Two kinds of bearer are accepted:

1. A Keycloak access token (realm `workshop`, client `devops-tile`) — verified against the realm's JWKS.
   The learner name is `preferred_username`; roles come from the `roles` claim or `realm_access.roles`.
   Learners may act only on their own environments; instructors on anyone's.
2. The static AGENT_TOKEN from .env — break-glass / CLI. Treated as an instructor named "cli".

If KEYCLOAK_ISSUER is empty (laptop sandbox), only the static token is accepted — nothing changes for phase 1/2.
"""
from dataclasses import dataclass, field
from fastapi import Header, HTTPException
from . import config

try:
    import jwt
    from jwt import PyJWKClient
except ImportError:  # pragma: no cover - requirements.txt installs it
    jwt = None
    PyJWKClient = None

_jwks = None


def _client():
    global _jwks
    if _jwks is None:
        _jwks = PyJWKClient(config.KEYCLOAK_JWKS_URL, cache_keys=True, lifespan=3600)
    return _jwks


@dataclass
class Principal:
    name: str
    roles: set[str] = field(default_factory=set)
    static: bool = False

    @property
    def instructor(self) -> bool:
        return self.static or "instructor" in self.roles

    def can_act_on(self, learner: str) -> bool:
        return self.instructor or learner == self.name


def _deny(detail: str):
    raise HTTPException(401, {"error": "unauthorized", "detail": detail})


def _from_keycloak(token: str) -> Principal:
    if jwt is None:
        _deny("PyJWT not installed; pip install -r agent/requirements.txt")
    try:
        key = _client().get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=["RS256"],
            audience=config.KEYCLOAK_AUDIENCE, issuer=config.KEYCLOAK_ISSUER,
            options={"require": ["exp", "iss"]}, leeway=30,
        )
    except jwt.ExpiredSignatureError:
        _deny("token expired — sign in again")
    except jwt.InvalidAudienceError:
        _deny(f"token audience is not {config.KEYCLOAK_AUDIENCE} (check the devops-tile client's audience mapper)")
    except jwt.InvalidIssuerError:
        _deny(f"token issuer is not {config.KEYCLOAK_ISSUER}")
    except Exception as e:  # noqa: BLE001 — bad signature, malformed, JWKS unreachable
        _deny(f"token rejected: {type(e).__name__}: {e}")
    name = claims.get("preferred_username") or claims.get("sub")
    roles = set(claims.get("roles") or []) | set((claims.get("realm_access") or {}).get("roles") or [])
    return Principal(name=name, roles=roles)


def current_user(authorization: str | None = Header(default=None)) -> Principal:
    """FastAPI dependency. 401 unless the bearer is the static token or a valid Keycloak token."""
    if not authorization or not authorization.startswith("Bearer "):
        _deny("missing bearer token")
    token = authorization[7:].strip()
    if token and token == config.AGENT_TOKEN:
        return Principal(name="cli", roles={"instructor"}, static=True)
    if not config.KEYCLOAK_ISSUER:
        _deny("bad bearer token")
    return _from_keycloak(token)


def require(principal: Principal, learner: str):
    """403 when a learner reaches for someone else's environment."""
    if not principal.can_act_on(learner):
        raise HTTPException(403, {"error": "forbidden", "detail": f"{principal.name} may only act on their own environment"})
