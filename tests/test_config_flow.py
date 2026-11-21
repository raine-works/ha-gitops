"""Adding a repository: HTTPS straight to the webhook step, SSH through its deploy key."""

from pathlib import Path
from unittest.mock import patch

import pytest

from custom_components.gitops.const import CONF_KEY_ID, DOMAIN, KEYS_FOLDER
from custom_components.gitops.git import GitError
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import Origin


@pytest.fixture(autouse=True)
def config_dir(hass: HomeAssistant, tmp_path: Path) -> Path:
    folder = tmp_path / "config"
    folder.mkdir()
    hass.config.config_dir = str(folder)
    return folder


async def test_a_reachable_repository(hass: HomeAssistant, origin: Origin) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"url": origin.url, "branch": "main"}
    )
    assert result["step_id"] == "webhook"
    with patch("custom_components.gitops.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["folder"] == "origin" and result["data"]["secret"]


async def test_bad_folders_and_branches(
    hass: HomeAssistant, origin: Origin, config_dir: Path
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"url": origin.url, "branch": "main", "folder": "custom_components"},
    )
    assert result["errors"] == {"folder": "bad_folder"}
    (config_dir / "packages").mkdir()
    (config_dir / "packages" / "mine.yaml").write_text("a: 1\n")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"url": origin.url, "branch": "main", "folder": "packages"}
    )
    assert result["errors"] == {"folder": "folder_in_use"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"url": origin.url, "branch": "nope", "folder": "home"}
    )
    assert result["errors"] == {"base": "cannot_access"}


async def test_ssh_makes_a_deploy_key(hass: HomeAssistant, config_dir: Path) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.gitops.config_flow.Repo.remote_head",
        side_effect=GitError("Permission denied"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"url": "git@github.com:me/home.git", "branch": "main"}
        )
        assert result["step_id"] == "deploy_key"
        assert result["description_placeholders"]["public_key"].startswith(
            "ssh-ed25519 "
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        assert result["errors"] == {"base": "cannot_access"}
    with patch(
        "custom_components.gitops.config_flow.Repo.remote_head", return_value="abc"
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "webhook"
    with patch("custom_components.gitops.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    key = config_dir / KEYS_FOLDER / result["data"][CONF_KEY_ID] / "id_ed25519"
    assert key.is_file() and oct(key.stat().st_mode)[-3:] == "600"
