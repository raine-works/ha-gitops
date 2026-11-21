"""Load custom_components/gitops, against real Git repositories made per test."""

from pathlib import Path
import subprocess

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load the integration from custom_components/."""


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


class Origin:
    """A bare repository with a working copy that commits and pushes to it."""

    def __init__(self, root: Path) -> None:
        self.bare = root / "origin.git"
        self.work = root / "work"
        git(root, "init", "-q", "--bare", "-b", "main", str(self.bare))
        git(root, "clone", "-q", str(self.bare), str(self.work))
        git(self.work, "config", "user.email", "test@example.com")
        git(self.work, "config", "user.name", "Test")
        git(self.work, "checkout", "-q", "-b", "main")

    @property
    def url(self) -> str:
        return str(self.bare)

    def commit(self, files: dict[str, str], message: str = "Change") -> str:
        for name, text in files.items():
            path = self.work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        git(self.work, "add", "-A")
        git(self.work, "commit", "-q", "-m", message)
        git(self.work, "push", "-q", "origin", "main")
        return git(self.work, "rev-parse", "HEAD")


@pytest.fixture
def origin(tmp_path: Path) -> Origin:
    """A repository with one commit."""
    repo = Origin(tmp_path)
    repo.commit({"automations.yaml": "[]\n"}, "First")
    return repo
