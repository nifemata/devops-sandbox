# Lab 01 — The Golden Path

**Course:** DevOps track · **Time:** 60–90 min · **Mode:** individual, in the DevOps Sandbox

## What you will be able to do

By the end of this lab you will have taken one change all the way from your
editor to a running service on Kubernetes, without touching the cluster by
hand, and you will be able to explain what happened at each of the five
stations in between.

## Before you start

You need: the sandbox running on your machine (`docker compose ps` shows
four containers healthy), your Gitea login, and `git`, `curl` and `kubectl`
installed. Open two things side by side: a terminal, and your browser on
`http://localhost:3000`.

## Part A — First trip down the path (20 min)

1. Copy the `hello` app folder somewhere of your own and make it a repository:

       git init -b main && git add -A && git commit -m "hello: first commit"
       git remote add origin http://localhost:3000/sandbox/hello.git
       git push -u origin main

2. In the browser open **sandbox/hello → Actions** and click the job that
   has just started. Watch the five steps run. For each one, write one line
   in your notes saying *what it did* and *what it would have cost you to do
   by hand*.

3. When step 5 is green, confirm the service is live:

       curl http://localhost:30080/
       kubectl -n sandbox get pods

   **Checkpoint 1:** the `version` field in the JSON matches the first seven
   characters of your commit hash (`git log --oneline -1`). Write both down.

## Part B — Change something (15 min)

4. Edit `app/main.py` so the greeting includes your name. Commit and push.
5. Watch the new job. Then run `curl http://localhost:30080/` a few times.

   **Checkpoint 2:** the message has changed, the `version` has changed, and
   `served_by` alternates between two pod names. Explain in one sentence why
   there are two.

## Part C — Break it on purpose (20 min)

6. Change `add()` so that it subtracts instead of adds. Push.
7. The pipeline should stop at step 2. Read the test output.

   **Checkpoint 3:** `curl http://localhost:30080/add?a=1&b=2` still returns
   3. Explain why the broken code never reached the cluster, and name the
   file that decides this.

8. Fix the function, push again, and confirm the pipeline is green.

## Part D — Break it later (15 min)

9. Now break something the tests do not cover: change the Dockerfile's
   `CMD` to run `app.wrong:app`. Push.
10. Step 5 will wait and then fail with a rollout timeout. Run
    `kubectl -n sandbox get pods` and `kubectl -n sandbox describe pod <one of the new ones>`.

    **Checkpoint 4:** `curl http://localhost:30080/` *still works*. Which
    Kubernetes setting kept the old pods serving? (Hint: look at the probes
    in `k8s/deployment.yaml`.)

11. Revert the Dockerfile change and push. Everything should go green.

## What to hand in

A short document with: the four checkpoints with your evidence (pasted
output is fine); your five one-line step descriptions from Part A; and one
paragraph answering: *"Which of the five stations would you remove if you
were forced to, and what would go wrong without it?"*

## Vocabulary you now own

pipeline · runner · unit test gate · container image · registry · tag ·
deployment · rolling update · readiness probe · NodePort

## Looking ahead

Next lab: we take `kubectl` out of the pipeline entirely and let Argo CD
keep the cluster matching the repository. Think about what breaks in today's
design if two people push at the same time.
