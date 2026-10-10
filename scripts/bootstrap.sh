#!/usr/bin/env bash
# One-shot bootstrap for the DevOps Sandbox. Safe to re-run.
#
#   1. starts Gitea, dind and k3s
#   2. creates the instructor account, the org and the "hello" repo
#   3. stores registry credentials as org secrets for CI
#   4. registers the Actions runner
#   5. copies a kubeconfig to ./kubeconfig.yaml for your laptop's kubectl
#
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || cp .env.example .env
# shellcheck disable=SC1091
set -a; . ./.env; set +a
: "${ADMIN_USER:=instructor}" "${ADMIN_PASS:=ChangeMe-Sandbox1}" "${ADMIN_EMAIL:=instructor@sandbox.local}" "${ORG:=sandbox}"

GITEA_URL="http://localhost:3000"
mkdir -p .bootstrap

say()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
api()  { # api METHOD PATH [JSON]
  local m="$1" p="$2" d="${3:-}"
  curl -sS -X "$m" -H "Authorization: token ${API_TOKEN}" -H "Content-Type: application/json" \
       ${d:+-d "$d"} "${GITEA_URL}/api/v1${p}"
}

say "Starting Gitea, dind and k3s"
docker compose up -d gitea dind k3s

say "Waiting for Gitea"
for _ in $(seq 1 60); do
  curl -fsS "${GITEA_URL}/api/healthz" >/dev/null 2>&1 && break
  sleep 2
done
curl -fsS "${GITEA_URL}/api/healthz" >/dev/null || { echo "Gitea did not come up"; exit 1; }

say "Instructor account: ${ADMIN_USER}"
docker compose exec -T -u git gitea gitea admin user create \
    --admin --username "${ADMIN_USER}" --password "${ADMIN_PASS}" --email "${ADMIN_EMAIL}" \
    --must-change-password=false 2>/dev/null \
  && echo "created" || echo "already exists"

say "API token"
if [ -s .bootstrap/api-token ]; then
  API_TOKEN="$(cat .bootstrap/api-token)"
else
  docker compose exec -T -u git gitea gitea admin user delete-access-token \
      --username "${ADMIN_USER}" sandbox-bootstrap >/dev/null 2>&1 || true
  API_TOKEN="$(docker compose exec -T -u git gitea gitea admin user generate-access-token \
      --username "${ADMIN_USER}" --token-name sandbox-bootstrap --scopes all --raw | tr -d '\r\n')"
  printf '%s' "${API_TOKEN}" > .bootstrap/api-token
fi
chmod 600 .bootstrap/api-token

say "Organisation: ${ORG}"
if api GET "/orgs/${ORG}" | grep -q '"username"'; then
  echo "already exists"
else
  api POST "/orgs" "{\"username\":\"${ORG}\",\"visibility\":\"public\",\"repo_admin_change_team_access\":true}" >/dev/null
  echo "created"
fi

say "Repository: ${ORG}/hello"
if api GET "/repos/${ORG}/hello" | grep -q '"full_name"'; then
  echo "already exists"
else
  api POST "/orgs/${ORG}/repos" '{"name":"hello","description":"Golden path sample app","default_branch":"main","auto_init":false,"private":false}' >/dev/null
  echo "created"
fi

say "CI secrets on the org (registry login)"
api PUT "/orgs/${ORG}/actions/secrets/REGISTRY_USER"  "{\"data\":\"${ADMIN_USER}\"}" >/dev/null
api PUT "/orgs/${ORG}/actions/secrets/REGISTRY_TOKEN" "{\"data\":\"${API_TOKEN}\"}" >/dev/null
echo "REGISTRY_USER / REGISTRY_TOKEN set"

say "Runner registration"
if [ -z "${RUNNER_TOKEN:-}" ]; then
  RUNNER_TOKEN="$(docker compose exec -T -u git gitea gitea actions generate-runner-token | tr -d '\r\n')"
  if grep -q '^RUNNER_TOKEN=' .env; then
    sed -i.bak "s|^RUNNER_TOKEN=.*|RUNNER_TOKEN=${RUNNER_TOKEN}|" .env && rm -f .env.bak
  else
    echo "RUNNER_TOKEN=${RUNNER_TOKEN}" >> .env
  fi
fi
docker compose up -d --build runner
echo "runner starting (check: ${GITEA_URL}/-/admin/actions/runners)"

say "kubeconfig for your laptop"
for _ in $(seq 1 60); do
  docker compose exec -T k3s test -s /output/kubeconfig.yaml 2>/dev/null && break
  sleep 2
done
docker compose cp k3s:/output/kubeconfig.yaml ./kubeconfig.yaml
chmod 600 kubeconfig.yaml
echo "./kubeconfig.yaml written  (export KUBECONFIG=\$PWD/kubeconfig.yaml)"

cat <<EOF

------------------------------------------------------------------
 DevOps Sandbox is up.

   Gitea (git, CI, registry) : ${GITEA_URL}       login ${ADMIN_USER} / ${ADMIN_PASS}
   Runner admin page         : ${GITEA_URL}/-/admin/actions/runners
   Kubernetes                : export KUBECONFIG=\$PWD/kubeconfig.yaml && kubectl get nodes
   Sample app (after Lab 01) : http://localhost:30080

 Next: follow docs/LAB-01-golden-path.md  (push sample-app/hello to ${ORG}/hello)
------------------------------------------------------------------
EOF
