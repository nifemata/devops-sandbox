# DevOps Sandbox — the golden path, on one laptop

A complete, end-to-end DevOps loop small enough to run on a MacBook with
Docker Desktop, and honest enough that every step is a plain command a
student can read:

```
 you                 Gitea (git · CI · registry)          runner              dind            k3s
 ───                 ────────────────────────────         ──────              ────            ───
 git push  ───────▶  repo sandbox/hello
                     Actions sees the push  ──────────▶   clone
                                                          pytest
                                                          docker build ───▶  image
                                                          docker push  ───▶  gitea:3000/sandbox/hello:<sha>
                                                          kubectl apply ───────────────────────▶ Deployment
                                                          kubectl set image                      pulls image
                                                                                                 from gitea:3000
 browser  ◀──────────────────────────────────────────────────────────────────────────────────  http://localhost:30080
```

Four containers on one private Docker network. Inside the network Gitea is
`gitea:3000`; from your laptop it is `http://localhost:3000`.

| Container | Image | Role |
|-----------|-------|------|
| `gitea`   | `gitea/gitea:1.24` | Git hosting, Gitea Actions (GitHub-Actions-compatible CI), container registry |
| `runner`  | built from `runner/` | Runs pipeline steps in *host mode* (inside its own container): git, python, docker CLI, kubectl |
| `dind`    | `docker:dind` | A private Docker daemon that builds and pushes images. Your laptop's daemon is never used by CI |
| `k3s`     | `rancher/k3s` | A real single-node Kubernetes; pulls straight from `gitea:3000`; app exposed as NodePort 30080 |

This is deliberately the *smallest* thing that is still real. Argo CD,
Prometheus/Grafana, Keycloak, Vault and Trivy each slot in later as one more
container or one more Helm release — see "What comes next".

## Prerequisites

* Docker Desktop (Apple Silicon or Intel) with **at least 6 GB** memory
  allocated (Settings → Resources). The stack idles at about 2.5 GB.
* `git`, `curl`, and `kubectl` on the laptop (`brew install kubectl`).
* Ports 3000, 2222, 6443, 30080, 30081 free.

## Quick start (≈ 10 minutes, mostly image pulls)

```bash
cd devops-sandbox
cp .env.example .env          # optional: change ADMIN_PASS / ORG first
./scripts/bootstrap.sh
```

Bootstrap starts the containers, creates the `instructor` account, the
`sandbox` organisation and the empty `sandbox/hello` repository, stores
registry credentials as org-level CI secrets, registers the runner and
copies a kubeconfig to `./kubeconfig.yaml`. Re-running it is safe.

Check it is alive:

```bash
open http://localhost:3000                     # Gitea — log in as instructor
export KUBECONFIG=$PWD/kubeconfig.yaml
kubectl get nodes                              # one node, Ready
```

The runner should show as idle at `http://localhost:3000/-/admin/actions/runners`
(give it a minute after bootstrap; it builds its image on first run).

## Walk the golden path

Push the sample app and watch the pipeline do the rest:

```bash
cd sample-app/hello
git init -b main && git add -A && git commit -m "hello: first commit"
git remote add origin http://localhost:3000/sandbox/hello.git
git push -u origin main                        # user: instructor, password: from .env
```

Open `http://localhost:3000/sandbox/hello/actions`, click the running job,
and read the five steps as they happen. When step 5 finishes:

```bash
curl http://localhost:30080/                   # {"message": "...", "version": "<sha>", "served_by": "hello-..."}
kubectl -n sandbox get pods
```

That round trip — commit → test → image → registry → cluster → URL — is
Lab 01. `docs/LAB-01-golden-path.md` is the one-page student version.

## How the pieces find each other

* The runner clones from `gitea:3000` using the org secret `REGISTRY_TOKEN`
  (an instructor API token). Students in their own orgs get their own token
  as an org secret — bootstrap shows the two API calls.
* `docker` commands in the runner talk to `dind` via `DOCKER_HOST=tcp://dind:2375`.
  dind is started with `--insecure-registry=gitea:3000`, so pushes are plain HTTP.
* k3s pulls from `gitea:3000` because `k3s/registries.yaml` declares it an
  HTTP mirror; the org is public, so pulls need no credentials.
* The runner reads the cluster's kubeconfig from the shared `kube` volume
  and rewrites `127.0.0.1` to `k3s`. Your laptop uses the same file unchanged
  because port 6443 is published.

## Everyday commands

```bash
docker compose ps                              # health of the four containers
docker compose logs -f runner                  # watch a job from the runner's side
docker compose exec dind docker images         # what CI has built
kubectl -n sandbox get all                     # what is running
docker compose stop / start                    # pause the sandbox, keep everything
./scripts/reset.sh                             # wipe it all (between cohorts)
```

## Troubleshooting

**Job stays "waiting".** The runner is not registered or has the wrong label.
`docker compose logs runner`; if it says the token was rejected, blank
`RUNNER_TOKEN=` in `.env` and re-run bootstrap. Jobs must use `runs-on: host`.

**Step 1 fails with authentication error.** The org secrets are missing
(bootstrap re-creates them) or the repo lives outside the `sandbox` org.

**Step 4 `http: server gave HTTP response to HTTPS client`.** dind lost its
`--insecure-registry` flag — `docker compose up -d --force-recreate dind`.

**Step 5 `ImagePullBackOff`.** k3s cannot reach the registry: confirm
`k3s/registries.yaml` is mounted (`docker compose exec k3s cat /etc/rancher/k3s/registries.yaml`)
and the org/package is public (Gitea → sandbox → Packages).

**k3s restarts in a loop on Apple Silicon.** Raise Docker Desktop memory; k3s
wants about 1 GB on its own.

**Port 3000 already in use.** Another dev server; change the published port in
`docker-compose.yml` *and* `GITEA__server__ROOT_URL`.

## What comes next (each is its own lab)

1. **Argo CD / GitOps** — `./scripts/add-argocd.sh` installs it on :30081.
   Lab 02: delete the `kubectl` lines from the pipeline and let Argo reconcile `k8s/` instead.
2. **Observability** — Prometheus + Grafana via the kube-prometheus-stack Helm chart; add a
   `/metrics` endpoint to hello. Lab 03: find the slow request.
3. **Infrastructure as Code** — Terraform/OpenTofu with the Gitea provider creating the
   per-student org, repo and secrets that bootstrap now does with curl.
4. **Identity** — Keycloak as the single login for Gitea, Argo CD and Grafana.
5. **Supply-chain security** — Trivy scanning the image between steps 3 and 4; fail the build on CRITICAL.
6. **Per-student tenancy** — one org per student, one namespace per student with a ResourceQuota,
   runner label per cohort. This is the point at which it becomes a SIT Lab tile backed by a
   `devops-agent` on a dedicated host, exactly as the Network Lab is backed by `netlab-agent`.

Rule of thumb carried over from the SIT Lab: a new tool joins the stack only
after the previous lab runs green end to end.

## Before `docker compose up`

1. Add `127.0.0.1 gitea` to `/etc/hosts` (macOS/Linux) or
   `C:\Windows\System32\drivers\etc\hosts` (Windows). Gitea, the runner
   and the registry all use the hostname `gitea`; the browser must too.
2. Open Gitea at http://gitea:3000, not localhost:3000.
   The deployed app is still served at http://localhost:30080.

Note: `GITEA__server__ROOT_URL` in docker-compose.yml is rewritten into
app.ini on every start. Change configuration in compose, not inside the
container.
