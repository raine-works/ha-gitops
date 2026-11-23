"""Deploys against real Git repositories: clone, pull, check, roll back, reload, webhook."""

import hashlib
import hmac
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pytest_homeassistant.common import (
    MockConfigEntry,
    async_capture_events,
    async_mock_service,
)

from custom_components.gitops import push_branch
from custom_components.gitops.config_flow import clean_folder
from custom_components.gitops.const import (
    CONF_BRANCH,
    CONF_FOLDER,
    CONF_RELOAD,
    CONF_RELOAD_DOMAINS,
    CONF_SECRET,
    CONF_URL,
    CONF_WEBHOOK_ID,
    DOMAIN,
    EVENT_DEPLOYED,
    EVENT_FAILED,
    RELOAD_DOMAINS,
)
from custom_components.gitops.git import is_ssh, repo_name
from homeassistant.core import HomeAssistant

from .conftest import Origin, git

SECRET = "s3cret"


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def config_dir(hass: HomeAssistant, tmp_path: Path) -> Path:
    """A /config of the test's own, so clones and keys land in tmp_path."""
    folder = tmp_path / "config"
    folder.mkdir()
    hass.config.config_dir = str(folder)
    return folder


async def setup(hass: HomeAssistant, origin: Origin, **options) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="home",
        unique_id="home",
        data={
            CONF_URL: origin.url,
            CONF_BRANCH: "main",
            CONF_FOLDER: "home",
            CONF_WEBHOOK_ID: "hook",
            CONF_SECRET: SECRET,
        },
        options={
            CONF_RELOAD: RELOAD_DOMAINS,
            CONF_RELOAD_DOMAINS: ["automation"],
            **options,
        },
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.gitops.deploy.async_check_ha_config_file",
        return_value=SimpleNamespace(errors=[]),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    return entry


def test_urls_and_folders() -> None:
    assert is_ssh("git@github.com:me/home.git") and is_ssh("ssh://git@host/me/home")
    assert not is_ssh("https://github.com/me/home.git")
    assert repo_name("git@github.com:me/my-home.git") == "my-home"
    assert clean_folder("/my-home/") == "my-home"
    assert clean_folder("repos/home") == "repos/home"
    for bad in (
        "",
        "..",
        "../etc",
        "custom_components",
        "www/x",
        ".storage",
        ".hidden",
    ):
        assert clean_folder(bad) is None, bad


def test_webhook_requests() -> None:
    body = json.dumps({"ref": "refs/heads/main"}).encode()
    github = {"X-Hub-Signature-256": sign(body), "X-GitHub-Event": "push"}
    assert push_branch(github, body, SECRET) == (True, "main")
    assert push_branch(
        {**github, "X-Hub-Signature-256": "sha256=00"}, body, SECRET
    ) == (False, None)
    assert push_branch({**github, "X-GitHub-Event": "ping"}, body, SECRET) == (
        True,
        None,
    )
    assert push_branch({}, body, SECRET) == (False, None)
    gitlab = {"X-Gitlab-Token": SECRET, "X-Gitlab-Event": "Push Hook"}
    assert push_branch(gitlab, body, SECRET) == (True, "main")
    tag = json.dumps({"ref": "refs/tags/v1"}).encode()
    assert push_branch({**github, "X-Hub-Signature-256": sign(tag)}, tag, SECRET) == (
        True,
        None,
    )


async def test_clones_then_deploys_each_push(
    hass: HomeAssistant, origin: Origin, config_dir: Path
) -> None:
    """Set up clones it; a new commit is pulled, its changes listed, and automations reloaded."""
    reloads = async_mock_service(hass, "automation", "reload")
    deployed = async_capture_events(hass, EVENT_DEPLOYED)
    entry = await setup(hass, origin)
    assert (config_dir / "home" / "automations.yaml").is_file()
    assert hass.states.get("sensor.home_status").state == "deployed"
    assert len(reloads) == 1

    commit = origin.commit({"scripts/new.yaml": "x: {}\n"}, "Add a script")
    with patch(
        "custom_components.gitops.deploy.async_check_ha_config_file",
        return_value=SimpleNamespace(errors=[]),
    ):
        result = await entry.runtime_data.async_deploy("test")
    assert result.status == "deployed" and result.commit == commit
    assert result.changed == ["scripts/new.yaml"] and result.subject == "Add a script"
    assert (
        deployed[-1].data["commit"] == commit and deployed[-1].data["folder"] == "home"
    )
    assert len(reloads) == 2

    # Nothing new: nothing reloads
    result = await entry.runtime_data.async_deploy("test")
    assert result.status == "unchanged" and len(reloads) == 2


async def test_local_edits_are_discarded(
    hass: HomeAssistant, origin: Origin, config_dir: Path
) -> None:
    entry = await setup(hass, origin)
    (config_dir / "home" / "automations.yaml").write_text("edited in Home Assistant\n")
    origin.commit({"other.yaml": "a: 1\n"})
    with patch(
        "custom_components.gitops.deploy.async_check_ha_config_file",
        return_value=SimpleNamespace(errors=[]),
    ):
        await entry.runtime_data.async_deploy("test")
    assert (config_dir / "home" / "automations.yaml").read_text() == "[]\n"


async def test_a_failing_check_rolls_back(
    hass: HomeAssistant, origin: Origin, config_dir: Path
) -> None:
    """The folder goes back to the commit it had, nothing reloads, and a notification says why."""
    reloads = async_mock_service(hass, "automation", "reload")
    failed = async_capture_events(hass, EVENT_FAILED)
    entry = await setup(hass, origin)
    good = git(config_dir / "home", "rev-parse", "HEAD")
    origin.commit({"automations.yaml": "broken: [\n"}, "Break it")
    bad = SimpleNamespace(
        errors=[SimpleNamespace(domain="automation", message="Invalid config")]
    )
    with patch(
        "custom_components.gitops.deploy.async_check_ha_config_file", return_value=bad
    ):
        result = await entry.runtime_data.async_deploy("test")
    assert (
        result.status == "rolled_back" and "automation: Invalid config" in result.error
    )
    assert git(config_dir / "home", "rev-parse", "HEAD") == good
    assert (config_dir / "home" / "automations.yaml").read_text() == "[]\n"
    assert len(reloads) == 1  # only the first clone's
    assert failed[-1].data["status"] == "rolled_back"
    assert hass.states.get("sensor.home_status").state == "rolled_back"
    notifications = hass.data["persistent_notification"]
    assert f"gitops_{entry.entry_id}" in notifications


async def test_the_check_cannot_be_skipped(
    hass: HomeAssistant, origin: Origin, config_dir: Path
) -> None:
    """An entry saved with the old check_config option off is still checked: a failing configuration never reloads."""
    reloads = async_mock_service(hass, "automation", "reload")
    entry = await setup(hass, origin, check_config=False)
    good = git(config_dir / "home", "rev-parse", "HEAD")
    origin.commit({"automations.yaml": "broken: [\n"}, "Break it")
    bad = SimpleNamespace(errors=[SimpleNamespace(domain=None, message="Bad YAML")])
    with patch(
        "custom_components.gitops.deploy.async_check_ha_config_file", return_value=bad
    ):
        result = await entry.runtime_data.async_deploy("test")
    assert result.status == "rolled_back" and result.error == "Bad YAML"
    assert git(config_dir / "home", "rev-parse", "HEAD") == good
    assert len(reloads) == 1  # only the first clone's


async def test_an_unreachable_repository_fails(
    hass: HomeAssistant, origin: Origin, tmp_path: Path
) -> None:
    entry = await setup(hass, origin)
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_URL: str(tmp_path / "missing.git")}
    )
    result = await entry.runtime_data.async_deploy("test")
    assert result.status == "failed" and result.error


async def test_the_webhook_deploys_its_branch(
    hass: HomeAssistant, origin: Origin, hass_client_no_auth
) -> None:
    entry = await setup(hass, origin)
    client = await hass_client_no_auth()
    commit = origin.commit({"pushed.yaml": "a: 1\n"})
    body = json.dumps({"ref": "refs/heads/main"}).encode()

    refused = await client.post(
        "/api/webhook/hook", data=body, headers={"X-GitHub-Event": "push"}
    )
    assert refused.status == 401

    with patch(
        "custom_components.gitops.deploy.async_check_ha_config_file",
        return_value=SimpleNamespace(errors=[]),
    ):
        response = await client.post(
            "/api/webhook/hook",
            data=body,
            headers={"X-GitHub-Event": "push", "X-Hub-Signature-256": sign(body)},
        )
        assert response.status == 202
        await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.runtime_data.last.commit == commit


async def test_the_deploy_action(hass: HomeAssistant, origin: Origin) -> None:
    entry = await setup(hass, origin)
    response = await hass.services.async_call(
        DOMAIN, "deploy", {}, blocking=True, return_response=True
    )
    assert response["deploys"][entry.entry_id]["status"] == "unchanged"
