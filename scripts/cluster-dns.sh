#!/usr/bin/env bash
# Teach the k3s cluster DNS the compose hostname "gitea" so pods (tests, kaniko) can reach the registry.
set -euo pipefail
cd "$(dirname "$0")/.."
export KUBECONFIG=$PWD/kubeconfig.yaml
GITEA_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' devops-sandbox-gitea-1)
kubectl -n kube-system delete configmap coredns-custom --ignore-not-found
kubectl -n kube-system create configmap coredns-custom \
  --from-literal=gitea.server="gitea:53 {
  hosts {
    ${GITEA_IP} gitea
  }
}"
kubectl -n kube-system rollout restart deployment/coredns
kubectl -n kube-system rollout status deployment/coredns --timeout=90s
echo "cluster DNS: gitea -> ${GITEA_IP}"
