"""Run a lab's grade.yaml against the live environment. Read-only by contract."""
import json
from datetime import datetime, timezone
import yaml
from . import config
from .clients import Gitea, Kube, http_get


def _subst(value, learner: str, head: str):
    if isinstance(value, str):
        return value.replace("<learner>", learner).replace("head-sha-7", head[:7])
    if isinstance(value, dict):
        return {k: _subst(v, learner, head) for k, v in value.items()}
    if isinstance(value, list):
        return [_subst(v, learner, head) for v in value]
    return value


def _match(expect: dict, actual: dict) -> tuple[bool, dict]:
    """Every key in expect must equal the same key in actual."""
    got = {k: actual.get(k) for k in expect}
    return all(actual.get(k) == v for k, v in expect.items()), got


def grade(learner: str, lab: str, overrides: dict | None = None) -> dict:
    manifest = yaml.safe_load((config.LABS_DIR / lab / "grade.yaml").read_text())
    owner = (overrides or {}).get("owner") or manifest.get("owner", learner)
    gitea, kube = Gitea(), Kube()

    head = ""
    repo_for_head = next((c["repo"] for c in manifest["checks"] if c["kind"] == "gitea-run"), None)
    if repo_for_head:
        try:
            head = gitea.head_sha(owner, repo_for_head)
        except Exception as e:  # noqa: BLE001
            head = ""
            head_err = str(e)

    results = []
    for raw in manifest["checks"]:
        chk = _subst(raw, learner, head or "0000000")
        kind = chk["kind"]
        ok, evidence = False, {}
        try:
            if kind == "gitea-run":
                run = gitea.latest_run(owner, chk["repo"], chk.get("workflow"), chk.get("branch", "main"))
                if run is None:
                    evidence = {"error": "no run found"}
                else:
                    status = run.get("conclusion") or run.get("status")
                    evidence = {"run": run.get("run_number", run.get("id")), "status": status,
                                "commit": (run.get("head_sha") or "")[:7]}
                    ok = status == chk["expect"]
            elif kind == "k8s-deploy":
                d = kube.get("deployment", chk["name"], chk.get("namespace"))
                if d is None:
                    evidence = {"error": "deployment not found"}
                else:
                    st = d.get("status", {})
                    evidence = {"ready": st.get("readyReplicas", 0), "desired": d["spec"].get("replicas", 1)}
                    ok = evidence["ready"] >= chk["expect"]["ready"]
            elif kind == "image-tag":
                d = kube.get("deployment", chk["deployment"], chk.get("namespace"))
                if d is None:
                    evidence = {"error": "deployment not found"}
                else:
                    image = d["spec"]["template"]["spec"]["containers"][0]["image"]
                    reg, _, tag = image.rpartition(":")
                    evidence = {"image": image, "head": head[:7]}
                    ok = reg == chk["registry"] and tag == chk["tag"]
            elif kind == "http":
                code, body = http_get(chk["url"])
                evidence = {"status": code}
                ok = code == chk.get("expect", {}).get("status", 200)
                if ok and "json" in chk["expect"]:
                    try:
                        ok, got = _match(chk["expect"]["json"], json.loads(body))
                        evidence["json"] = got
                    except ValueError:
                        ok, evidence["body"] = False, body[:200]
            elif kind == "k8s-object":
                o = kube.get(chk["object"], chk["name"], chk.get("namespace"))
                exists = o is not None
                ok = exists == chk.get("exists", True)
                evidence = {"exists": exists}
                if ok and o and "fields" in chk:
                    ok, got = _match(chk["fields"], o)
                    evidence["fields"] = got
            else:
                evidence = {"error": f"unknown check kind {kind}"}
        except Exception as e:  # noqa: BLE001
            evidence = {"error": str(e)}
        results.append({"kind": kind, "ok": ok, "evidence": evidence})

    report = {"learner": learner, "lab": lab, "head": head[:7],
              "score": sum(r["ok"] for r in results), "of": len(results),
              "checks": results, "graded_at": datetime.now(timezone.utc).isoformat()}
    (config.STATE_DIR / f"{learner}.{lab}.grade.json").write_text(json.dumps(report, indent=2))
    return report
