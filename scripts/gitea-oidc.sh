#!/usr/bin/env bash
# Point Gitea's sign-in at Keycloak (realm `workshop`, confidential client `gitea`). Safe to re-run:
# creates the auth source "keycloak" once, updates it afterwards. No Gitea restart needed.
#
# Needs in .env:   KEYCLOAK_ISSUER=https://devops-auth.mubita.digital/realms/workshop
#                  GITEA_OIDC_SECRET=<secret of the Keycloak client `gitea`>
# Optional:        GITEA_OIDC_NAME=keycloak   GITEA_OIDC_CLIENT=gitea
#
# Keycloak side (admin console, realm workshop -> Clients -> gitea): Client authentication ON,
# Standard flow ON, Valid redirect URI  <GITEA_ROOT_URL>/user/oauth2/<GITEA_OIDC_NAME>/callback
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
set -a; . ./.env; set +a
: "${KEYCLOAK_ISSUER:?set KEYCLOAK_ISSUER in .env}" "${GITEA_OIDC_SECRET:?set GITEA_OIDC_SECRET in .env}"
NAME="${GITEA_OIDC_NAME:-keycloak}"
CLIENT="${GITEA_OIDC_CLIENT:-gitea}"
DISCOVERY="${KEYCLOAK_ISSUER%/}/.well-known/openid-configuration"

g() { docker compose exec -T -u git gitea gitea "$@"; }

echo "==> checking Gitea can reach ${DISCOVERY}"
docker compose exec -T gitea curl -fsS -o /dev/null "${DISCOVERY}" || { echo "Gitea container cannot reach Keycloak's discovery URL"; exit 1; }

ARGS=(--name "${NAME}" --provider openidConnect --key "${CLIENT}" --secret "${GITEA_OIDC_SECRET}"
      --auto-discover-url "${DISCOVERY}" --scopes openid --scopes profile --scopes email --skip-local-2fa)

ID="$(g admin auth list | awk -v n="${NAME}" 'NR>1 && $2==n {print $1}' | tr -d '\r')"
if [ -n "${ID}" ]; then
  echo "==> updating auth source ${NAME} (id ${ID})"
  g admin auth update-oauth --id "${ID}" "${ARGS[@]}"
else
  echo "==> creating auth source ${NAME}"
  g admin auth add-oauth "${ARGS[@]}"
fi
g admin auth list
echo
echo "Done. Learners sign in at ${GITEA_ROOT_URL:-http://localhost:3000/}user/login -> 'Sign in with ${NAME}'"
echo "(direct link: ${GITEA_ROOT_URL:-http://localhost:3000/}user/oauth2/${NAME})"
