# hello

The golden-path sample app for the DevOps Sandbox. Push to `main` and the
pipeline in `.gitea/workflows/ci.yml` tests it, builds an image, pushes it to
the sandbox registry and rolls it out to the `sandbox` namespace in k3s.

Run locally:

    python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    pytest -q
    python -m app.main        # http://localhost:8080
