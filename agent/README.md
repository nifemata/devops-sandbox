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
