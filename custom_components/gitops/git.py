"""Git, run as a subprocess (Home Assistant's container ships it), and deploy keys."""

import asyncio
from dataclasses import dataclass
import os
from pathlib import Path
import re

GIT_TIMEOUT = 120
SSH_URL = re.compile(r"^(ssh://|[A-Za-z0-9._-]+@[A-Za-z0-9.-]+:)")
REPO_NAME = re.compile(r"([^/:]+?)(\.git)?/?$")


class GitError(Exception):
    """Git failed; the message is git's own (its last lines)."""


def is_ssh(url: str) -> bool:
    """An SSH remote (git@host:owner/repo, ssh://...), which needs a deploy key."""
    return bool(SSH_URL.match(url.strip()))


def repo_name(url: str) -> str:
    """The repository's name from its URL: git@github.com:owner/my-home.git -> my-home."""
    match = REPO_NAME.search(url.strip())
    return match.group(1) if match else "repository"


def generate_key(folder: Path) -> str:
    """Write a new ed25519 deploy key to folder (id_ed25519, 0600) and return its public key.

    Run in the executor.
    """
    # Imported here: only setup with an SSH remote needs it
    from cryptography.hazmat.primitives import serialization  # noqa: PLC0415
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: PLC0415

    folder.mkdir(parents=True, exist_ok=True)
    folder.chmod(0o700)
    key = Ed25519PrivateKey.generate()
    private = folder / "id_ed25519"
    private.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.OpenSSH,
            serialization.NoEncryption(),
        )
    )
    private.chmod(0o600)
    public = key.public_key().public_bytes(
        serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
    )
    text = public.decode() + " home-assistant-gitops"
    (folder / "id_ed25519.pub").write_text(text + "\n")
    return text


def read_public_key(folder: Path) -> str | None:
    """The deploy key's public half, if it's there. Run in the executor."""
    public = folder / "id_ed25519.pub"
    return public.read_text().strip() if public.is_file() else None


@dataclass
class Repo:
    """A remote branch and the folder it's kept in."""

    url: str
    branch: str
    path: Path
    keys: Path | None = None

    def _env(self) -> dict[str, str]:
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C")
        if self.keys is not None:
            env["GIT_SSH_COMMAND"] = (
                f"ssh -i {self.keys / 'id_ed25519'} -o IdentitiesOnly=yes"
                " -o StrictHostKeyChecking=accept-new"
                f" -o UserKnownHostsFile={self.keys / 'known_hosts'}"
                " -o BatchMode=yes"
            )
        return env

    async def git(self, *args: str, cwd: Path | None = None) -> str:
        """Run git; its stdout, or GitError with its stderr."""
        process = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=cwd,
            env=self._env(),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(process.communicate(), GIT_TIMEOUT)
        except TimeoutError as error:
            process.kill()
            await process.wait()
            raise GitError(
                f"git {args[0]} took over {GIT_TIMEOUT}s and was stopped"
            ) from error
        if process.returncode != 0:
            lines = (err or out).decode(errors="replace").strip().splitlines()
            raise GitError("\n".join(lines[-8:]) or f"git {args[0]} failed")
        return out.decode(errors="replace").strip()

    async def cloned(self) -> bool:
        """Whether the folder holds the clone.

        The check runs in a worker thread: it's called on Home Assistant's event loop.
        """
        return await asyncio.to_thread((self.path / ".git").is_dir)

    def _has_files(self) -> bool:
        """Whether the folder exists and has files in it. Blocking: run in a thread."""
        return self.path.exists() and any(self.path.iterdir())

    async def remote_head(self) -> str:
        """The branch's latest commit on the remote."""
        out = await self.git("ls-remote", "--", self.url, f"refs/heads/{self.branch}")
        if not out:
            raise GitError(f"The repository has no branch named {self.branch}")
        return out.split()[0]

    async def head(self) -> str | None:
        """The commit checked out, or None before the first clone."""
        if not await self.cloned():
            return None
        return await self.git("rev-parse", "HEAD", cwd=self.path)

    async def sync(self) -> str:
        """Clone, or fetch and reset to the remote branch; the new commit.

        The repository is the source of truth: local edits to tracked files are discarded,
        untracked files are left.
        """
        if not await self.cloned():
            if await asyncio.to_thread(self._has_files):
                raise GitError(
                    f"{self.path} already has files and isn't a clone of the repository"
                )
            await self.git(
                "clone",
                "--branch",
                self.branch,
                "--single-branch",
                "--",
                self.url,
                str(self.path),
            )
            return await self.git("rev-parse", "HEAD", cwd=self.path)
        if await self.git("remote", "get-url", "origin", cwd=self.path) != self.url:
            await self.git("remote", "set-url", "origin", self.url, cwd=self.path)
        await self.git(
            "fetch",
            "--prune",
            "origin",
            f"+refs/heads/{self.branch}:refs/remotes/origin/{self.branch}",
            cwd=self.path,
        )
        await self.reset(f"origin/{self.branch}")
        return await self.git("rev-parse", "HEAD", cwd=self.path)

    async def reset(self, ref: str) -> None:
        """Check the branch out at ref, discarding local edits."""
        await self.git("checkout", "--force", "-B", self.branch, ref, cwd=self.path)

    async def changed(self, old: str, new: str) -> list[str]:
        """The files that differ between two commits."""
        out = await self.git("diff", "--name-only", old, new, cwd=self.path)
        return out.splitlines() if out else []

    async def subject(self, commit: str) -> str:
        """A commit's first line."""
        return await self.git("log", "-1", "--format=%s", commit, cwd=self.path)
