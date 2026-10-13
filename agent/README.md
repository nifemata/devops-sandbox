# devops-agent (phase 2, step 2: grade)

Run from the devops-sandbox folder, against the sandbox that is already up:

    python3 -m venv .venv-agent && source .venv-agent/bin/activate
    pip install -r agent/requirements.txt
    export GITEA_PASSWORD='<instructor password>'     # or GITEA_TOKEN=<a Gitea access token>
    uvicorn agent.main:app --port 8900

Then, in another terminal:

    curl -s localhost:8900/healthz
    curl -s -X POST -H 'Authorization: Bearer dev-token' localhost:8900/v1/envs/local/01-golden-path/grade | python3 -m json.tool

Expected on a green Lab 01: `"score": 4, "of": 4`. The report is also written to agent/state/.

Settings (env or .env in the sandbox root): GITEA_URL (default http://gitea:3000), GITEA_USER (instructor),
GITEA_PASSWORD or GITEA_TOKEN, KUBECONFIG (default ./kubeconfig.yaml), AGENT_TOKEN (default dev-token).

provision / reset / fixture return 501 until build-plan steps 3–4.

## Gitea sign-in with Keycloak (patch 0005)

Learners open their repo and Actions logs with the same Keycloak account they use on the tile.

1. Keycloak admin console → realm `workshop` → Clients → `gitea` (confidential; created by the realm
   import on fresh installs, or by hand): Credentials tab → copy the client secret.
2. Sandbox `.env`: `GITEA_OIDC_SECRET=<that secret>` (KEYCLOAK_ISSUER is already there).
3. `docker compose up -d gitea` (picks up the `[service]`/`[oauth2_client]` settings), then `scripts/gitea-oidc.sh`.
4. Restart the agent. `GET /healthz` shows `gitea_oidc: keycloak`.

Provision then adds the learner to the **Owners** team of their own org (tenant labs only). If the learner
has not yet signed in to Gitea, the env record says `gitea_access: pending`; the next status call (tile
**Refresh**) retries. Every Keycloak user needs an email address — Gitea requires one to create the account.
