"""Publish the status of a Session Stats matrix run in its PR conversation."""

import argparse
import json
import os
import re
import subprocess


RESULTS = {"success": "Passed", "failure": "Failed", "cancelled": "Cancelled", "skipped": "Skipped"}


def positive_id(value):
    return re.fullmatch(r"[1-9][0-9]*", str(value or "")) is not None


def github_api(path, *args):
    return json.loads(subprocess.check_output(["gh", "api", path, *args], text=True, timeout=30))


def optional_metadata(api, path):
    try:
        value = api(path)
        return value if isinstance(value, dict) else {}
    except (subprocess.SubprocessError, ValueError):
        print(f"Could not resolve matrix metadata from {path}.")
        return {}


def find_comment(api, comments, marker):
    pages = api(f"{comments}?per_page=100", "--paginate", "--slurp")
    for page in pages:
        for comment in page:
            if (comment.get("user", {}).get("login") == "github-actions[bot]"
                    and marker in (comment.get("body") or "").splitlines()
                    and positive_id(comment.get("id"))):
                return str(comment["id"])
    return None


def result_links(api, prefix, run, attempt, run_url, artifact_id):
    links = []
    jobs = optional_metadata(api, f"{prefix}/actions/runs/{run}/attempts/{attempt}/jobs?per_page=100").get("jobs", [])
    job = next((row.get("id") for row in jobs if row.get("name") == "Downloadable HTML matrix"), None)
    if positive_id(job):
        links.append(f"[Report job]({run_url}/job/{job})")
    if positive_id(artifact_id):
        artifact = optional_metadata(api, f"{prefix}/actions/artifacts/{artifact_id}")
        if (str(artifact.get("id")) == artifact_id
                and str((artifact.get("workflow_run") or {}).get("id")) == run
                and artifact.get("name") == f"sessionstats-matrix-html-attempt-{attempt}"
                and artifact.get("expired") is False):
            links.append(f"[Download HTML report]({run_url}/artifacts/{artifact_id})")
    return links


def publish(phase, env, api=github_api):
    repo = env["GITHUB_REPOSITORY"]
    pr, command, run, attempt = (env[name] for name in
        ("PR_NUMBER", "COMMAND_ID", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"))
    coverage, sha = env["COVERAGE"], env["TARGET_SHA"]
    if not all(positive_id(value) for value in (pr, command, run, attempt)):
        raise ValueError("Invalid GitHub event or run metadata.")
    if (coverage not in ("smoke", "full", "exhaustive") or not re.fullmatch(r"[0-9a-f]{40}", sha)
            or not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", repo)):
        raise ValueError("Invalid matrix configuration.")

    prefix = f"repos/{repo}"
    repository_url = f'{env["GITHUB_SERVER_URL"].rstrip("/")}/{repo}'
    run_url = f"{repository_url}/actions/runs/{run}"
    command_url = f"{repository_url}/pull/{pr}#issuecomment-{command}"
    marker = f"<!-- sessionstats-matrix-run:{run}:{command}:{attempt} -->"
    comments = f"{prefix}/issues/{pr}/comments"
    links = [f"[Actions run]({run_url}/attempts/{attempt})"]
    if phase == "complete":
        status = RESULTS.get(env["REPORT_RESULT"], "Failed")
        links.extend(result_links(api, prefix, run, attempt, run_url, env.get("ARTIFACT_ID")))
    else:
        status = {"started": "Started", "running": "Running"}[phase]
    body = "\n\n".join((marker, f"**Session Stats Chromium `{coverage}` — {status}.**",
                         f"Commit `{sha[:12]}`, attempt {attempt}, from [this command]({command_url}).",
                         " · ".join(links)))

    # The start and running steps share one job. On a failed-jobs-only
    # retry, the completion job can run without a new announcement.
    comment_id = env.get("STATUS_COMMENT_ID") if phase == "running" else None
    if comment_id and not positive_id(comment_id):
        raise ValueError("Invalid status comment ID.")
    if not comment_id and phase != "started":
        comment_id = find_comment(api, comments, marker)
    if comment_id:
        response = api(f"{prefix}/issues/comments/{comment_id}", "--method", "PATCH", "-f", f"body={body}")
    else:
        response = api(comments, "--method", "POST", "-f", f"body={body}")
    published_id = response.get("id")
    if not positive_id(published_id) or (comment_id and str(published_id) != comment_id):
        raise ValueError("GitHub returned an unexpected status comment ID.")
    return published_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("started", "running", "complete"))
    options = parser.parse_args()
    try:
        comment_id = publish(options.phase, os.environ)
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"comment_id={comment_id}\n")
    except (KeyError, OSError, subprocess.SubprocessError, ValueError) as error:
        parser.exit(1, f"Could not publish the matrix status: {error}\n")


if __name__ == "__main__":
    main()
