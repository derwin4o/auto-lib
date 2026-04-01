import logging
import time
from typing import List

import requests

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubClient:
    def __init__(self, owner: str, repo: str, token: str):
        self._owner = owner
        self._repo = repo
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def _base(self) -> str:
        return f"{GITHUB_API}/repos/{self._owner}/{self._repo}"

    def get_labeled_issues(self, label_names: List[str]) -> List[dict]:
        """Return open issues that have at least one of label_names and are not labeled 'wip'."""
        resp = self._session.get(f"{self._base()}/issues", params={"state": "open", "per_page": 100})
        resp.raise_for_status()
        raw = resp.json()
        if len(raw) == 100:
            log.warning("get_labeled_issues for %s/%s returned 100 results — may be truncated", self._owner, self._repo)
        issues = []
        for issue in raw:
            if "pull_request" in issue:
                continue
            labels = {l["name"] for l in issue.get("labels", [])}
            if "wip" in labels:
                continue
            if labels & set(label_names):
                issues.append(issue)
        return issues

    def get_wip_issues(self) -> List[dict]:
        resp = self._session.get(f"{self._base()}/issues", params={"state": "open", "labels": "wip", "per_page": 100})
        resp.raise_for_status()
        return [i for i in resp.json() if "pull_request" not in i]

    def get_issue(self, issue_number: int) -> dict:
        resp = self._session.get(f"{self._base()}/issues/{issue_number}")
        resp.raise_for_status()
        data = resp.json()
        return {"number": data["number"], "title": data["title"],
                "body": data.get("body") or "", "labels": data.get("labels", [])}

    def add_label(self, issue_number: int, label: str):
        resp = self._session.post(f"{self._base()}/issues/{issue_number}/labels", json={"labels": [label]})
        resp.raise_for_status()

    def remove_label(self, issue_number: int, label: str):
        resp = self._session.delete(f"{self._base()}/issues/{issue_number}/labels/{label}")
        if resp.status_code not in (200, 404):
            resp.raise_for_status()

    def create_issue(self, title: str, body: str, labels: List[str]) -> dict:
        resp = self._session.post(f"{self._base()}/issues", json={"title": title, "body": body, "labels": labels})
        resp.raise_for_status()
        return resp.json()

    def create_pr(self, title: str, body: str, head: str, base: str = "main") -> dict:
        resp = self._session.post(f"{self._base()}/pulls", json={"title": title, "body": body, "head": head, "base": base})
        if not resp.ok:
            raise Exception(f"{resp.status_code} {resp.reason}: {resp.text}")
        return resp.json()

    def close_issue(self, issue_number: int, comment: str = None):
        if comment:
            self.post_comment(issue_number, comment)
        self._session.patch(f"{self._base()}/issues/{issue_number}", json={"state": "closed"}).raise_for_status()

    def post_comment(self, issue_number: int, body: str):
        self._session.post(f"{self._base()}/issues/{issue_number}/comments", json={"body": body}).raise_for_status()

    def merge_pr(self, pr_number: int, merge_method: str = "merge") -> bool:
        for attempt in range(4):
            resp = self._session.put(f"{self._base()}/pulls/{pr_number}/merge", json={"merge_method": merge_method})
            if resp.status_code == 200:
                return True
            if resp.status_code == 405:
                log.warning("PR #%d is not mergeable (conflict)", pr_number)
                return False
            if resp.status_code == 422 and attempt < 3:
                time.sleep(5)
                continue
            log.warning("PR #%d merge returned %d: %s", pr_number, resp.status_code, resp.text[:200])
            return False
        return False

    def is_pr_merged(self, pr_number: int) -> bool:
        resp = self._session.get(f"{self._base()}/pulls/{pr_number}")
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        return resp.json().get("merged", False)

    def delete_branch(self, branch: str):
        resp = self._session.delete(f"{self._base()}/git/refs/heads/{branch}")
        if resp.status_code not in (204, 422):
            resp.raise_for_status()

    def get_open_prs(self) -> List[dict]:
        resp = self._session.get(f"{self._base()}/pulls", params={"state": "open", "per_page": 100})
        resp.raise_for_status()
        return resp.json()

    def close_pr(self, pr_number: int, comment: str = None):
        if comment:
            self.post_comment(pr_number, comment)
        self._session.patch(f"{self._base()}/pulls/{pr_number}", json={"state": "closed"}).raise_for_status()

    def validate_labels(self, required_labels: List[str]):
        label_colors = {"easy": "228f3d", "hard": "d73a49", "architecture": "7057ff",
                        "wip": "ffd700", "auto-pr": "0366d6", "needs-planning": "fc2929", "auto": "228f3d"}
        resp = self._session.get(f"{self._base()}/labels", params={"per_page": 100})
        resp.raise_for_status()
        existing = {l["name"] for l in resp.json()}
        for label in required_labels:
            if label not in existing:
                color = label_colors.get(label, "cccccc")
                try:
                    self._session.post(f"{self._base()}/labels",
                                       json={"name": label, "color": color, "description": "Auto-created"})
                except Exception as e:
                    log.error("Error creating label '%s': %s", label, e)
