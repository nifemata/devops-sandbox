#!/usr/bin/env bash
# Lab 02 prep: install Argo CD into the sandbox cluster and expose its UI on :30081.
# Run after bootstrap.sh. Needs kubectl on your laptop.
set -euo pipefail
cd "$(dirname "$0")/.."
export KUBECONFIG="$PWD/kubeconfig.yaml"

kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# NodePort for the UI (plain HTTP inside the sandbox; --insecure tells Argo not to redirect to https)
kubectl -n argocd patch deployment argocd-server --type json -p '[
  {"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--insecure"}
]' || true
kubectl -n argocd patch svc argocd-server -p '{"spec":{"type":"NodePort","ports":[{"name":"http","port":80,"targetPort":8080,"nodePort":30081}]}}'

echo "Waiting for Argo CD to be ready..."
kubectl -n argocd rollout status deployment/argocd-server --timeout=300s

PASS="$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)"
cat <<EOF

 Argo CD UI : http://localhost:30081    login admin / ${PASS}

 To watch the hello app with GitOps, point an Application at
   repo  http://gitea:3000/sandbox/hello.git   path k8s/   namespace sandbox
EOF
