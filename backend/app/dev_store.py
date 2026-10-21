import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

STORE_FILE = Path(__file__).resolve().parent.parent / "dev_store.json"


class DevStore:
    """
    Lightweight, file-backed local persistence layer.
    Ensures users, imported repos, analyses, findings, and teams permanently
    persist across backend restarts even when PostgreSQL is offline.
    """

    def __init__(self, file_path: Path = STORE_FILE):
        self.file_path = file_path
        self._data: dict[str, Any] = {
            "users": [],
            "repositories": [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "owner_id": "00000000-0000-0000-0000-000000000000",
                    "name": "TREND-TECH-2",
                    "full_name": "Ajaymallavali/TREND-TECH-2",
                    "default_branch": "main",
                    "language": "JavaScript",
                    "imported_at": "2026-10-15T12:00:00Z",
                }
            ],
            "analyses": {},
            "findings": {},
            "organizations": [],
            "organization_members": [],
        }
        self.load()

    def load(self) -> None:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self._data.update(loaded)
            except Exception as exc:
                logger.warning(f"Could not load dev store from {self.file_path}: {exc}")

    def save(self) -> None:
        try:
            temp_path = self.file_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, default=str)
            if os.path.exists(temp_path):
                os.replace(temp_path, self.file_path)
        except Exception as exc:
            logger.warning(f"Could not save dev store to {self.file_path}: {exc}")

    # Users
    def get_users(self) -> list[dict[str, Any]]:
        return self._data.setdefault("users", [])

    def save_user(self, user: dict[str, Any]) -> None:
        users = self.get_users()
        for idx, u in enumerate(users):
            if u.get("id") == user.get("id") or u.get("email") == user.get("email"):
                users[idx] = user
                self.save()
                return
        users.append(user)
        self.save()

    def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        for u in self.get_users():
            if str(u.get("email", "")).lower() == email.lower():
                return u
        return None

    def find_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        for u in self.get_users():
            if str(u.get("id", "")) == str(user_id):
                return u
        return None

    # Repositories
    def get_repositories(self) -> list[dict[str, Any]]:
        return self._data.setdefault("repositories", [])

    def save_repository(self, repo: dict[str, Any]) -> None:
        repos = self.get_repositories()
        for idx, r in enumerate(repos):
            if r.get("id") == repo.get("id") or r.get("full_name") == repo.get("full_name"):
                repos[idx] = repo
                self.save()
                return
        repos.insert(0, repo)
        self.save()

    # Analyses & Findings
    def get_analyses(self) -> dict[str, dict[str, Any]]:
        return self._data.setdefault("analyses", {})

    def save_analysis(self, repo_id: str, analysis: dict[str, Any]) -> None:
        self.get_analyses()[str(repo_id)] = analysis
        self.save()

    def get_findings(self) -> dict[str, list[dict[str, Any]]]:
        return self._data.setdefault("findings", {})

    def save_findings(self, analysis_id: str, findings: list[dict[str, Any]]) -> None:
        self.get_findings()[str(analysis_id)] = findings
        self.save()

    # Organizations
    def get_organizations(self) -> list[dict[str, Any]]:
        return self._data.setdefault("organizations", [])

    def save_organization(self, org: dict[str, Any]) -> None:
        orgs = self.get_organizations()
        for idx, o in enumerate(orgs):
            if o.get("id") == org.get("id") or o.get("slug") == org.get("slug"):
                orgs[idx] = org
                self.save()
                return
        orgs.append(org)
        self.save()

    def get_organization_members(self) -> list[dict[str, Any]]:
        return self._data.setdefault("organization_members", [])

    def add_organization_member(self, member: dict[str, Any]) -> None:
        members = self.get_organization_members()
        for idx, m in enumerate(members):
            if m.get("organization_id") == member.get("organization_id") and m.get("user_id") == member.get("user_id"):
                members[idx] = member
                self.save()
                return
        members.append(member)
        self.save()


dev_store = DevStore()
