#!/usr/bin/env bash
# Wipe the sandbox completely (all repos, images, cluster state). Use between cohorts.
set -euo pipefail
cd "$(dirname "$0")/.."
read -r -p "This deletes every container and volume of the sandbox. Type RESET to continue: " ans
[ "$ans" = "RESET" ] || { echo "aborted"; exit 1; }
docker compose down -v --remove-orphans
rm -rf .bootstrap kubeconfig.yaml
sed -i.bak 's|^RUNNER_TOKEN=.*|RUNNER_TOKEN=|' .env 2>/dev/null && rm -f .env.bak || true
echo "clean. run scripts/bootstrap.sh to start again."
