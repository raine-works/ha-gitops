"""Set up a repository: its URL, branch and folder; a deploy key for SSH; the webhook to add."""

from pathlib import Path, PurePosixPath
import secrets
from typing import Any
import uuid

import probatio

from homeassistant.components import webhook
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.network import NoURLAvailableError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_BRANCH,
    CONF_FOLDER,
    CONF_KEY_ID,
    CONF_POLL_MINUTES,
    CONF_RELOAD,
    CONF_RELOAD_DOMAINS,
    CONF_SECRET,
    CONF_URL,
    CONF_WEBHOOK_ID,
    DEFAULT_BRANCH,
    DEFAULT_RELOAD_DOMAINS,
    DOMAIN,
    KEYS_FOLDER,
    RELOAD_ALL,
    RELOAD_DOMAINS,
    RELOAD_NONE,
    RESERVED_FOLDERS,
)
from .git import GitError, Repo, generate_key, is_ssh, repo_name


def clean_folder(folder: str) -> str | None:
    """The folder as a path under /config ("my-home", "repos/home"), or None.

    None when it's absolute, outside /config, /config itself, or one of Home Assistant's own.
    """
    path = PurePosixPath(folder.strip().strip("/"))
    if not path.parts or path.is_absolute() or ".." in path.parts:
        return None
    if path.parts[0] in RESERVED_FOLDERS or path.parts[0].startswith("."):
        return None
    return str(path)


def folder_in_use(path: Path, url: str) -> bool:
    """Files in the folder that aren't a clone (ours or of this URL). Run in the executor."""
    if not path.exists():
        return False
    if not path.is_dir():
        return True
    if not (path / ".git").is_dir():
        return any(path.iterdir())
    config = (path / ".git" / "config").read_text(errors="replace")
    return url not in config


class GitOpsConfigFlow(ConfigFlow, domain=DOMAIN):
    """A repository to deploy."""

    VERSION = 1

    def __init__(self) -> None:
        """Nothing chosen yet."""
        self._data: dict[str, Any] = {}
        self._public_key = ""

    def _repo(self) -> Repo:
        key_id = self._data.get(CONF_KEY_ID)
        return Repo(
            url=self._data[CONF_URL],
            branch=self._data[CONF_BRANCH],
            path=Path(self.hass.config.path(self._data[CONF_FOLDER])),
            keys=Path(self.hass.config.path(KEYS_FOLDER, key_id)) if key_id else None,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The repository, branch and folder."""
        errors: dict[str, str] = {}
        placeholders = {"error": ""}
        if user_input is not None:
            url = user_input[CONF_URL].strip()
            folder = clean_folder(user_input.get(CONF_FOLDER) or repo_name(url))
            branch = user_input[CONF_BRANCH].strip()
            if folder is None:
                errors[CONF_FOLDER] = "bad_folder"
            elif await self.hass.async_add_executor_job(
                folder_in_use, Path(self.hass.config.path(folder)), url
            ):
                errors[CONF_FOLDER] = "folder_in_use"
            else:
                await self.async_set_unique_id(folder)
                self._abort_if_unique_id_configured()
                self._data = {CONF_URL: url, CONF_BRANCH: branch, CONF_FOLDER: folder}
                if is_ssh(url):
                    key_id = uuid.uuid4().hex
                    self._data[CONF_KEY_ID] = key_id
                    self._public_key = await self.hass.async_add_executor_job(
                        generate_key, Path(self.hass.config.path(KEYS_FOLDER, key_id))
                    )
                    return await self.async_step_deploy_key()
                try:
                    await self._repo().remote_head()
                except GitError as error:
                    errors["base"] = "cannot_access"
                    placeholders["error"] = str(error)
                else:
                    return await self.async_step_webhook()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                probatio.Schema(
                    {
                        probatio.Required(CONF_URL): TextSelector(),
                        probatio.Required(
                            CONF_BRANCH, default=DEFAULT_BRANCH
                        ): TextSelector(),
                        probatio.Optional(CONF_FOLDER): TextSelector(),
                    }
                ),
                user_input,
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_deploy_key(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the deploy key to add to the repository (read access), then try it."""
        errors: dict[str, str] = {}
        placeholders = {"public_key": self._public_key, "error": ""}
        if user_input is not None:
            try:
                await self._repo().remote_head()
            except GitError as error:
                errors["base"] = "cannot_access"
                placeholders["error"] = str(error)
            else:
                return await self.async_step_webhook()
        return self.async_show_form(
            step_id="deploy_key",
            data_schema=probatio.Schema({}),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_webhook(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the webhook to add for instant deploys (polling works without it)."""
        if CONF_WEBHOOK_ID not in self._data:
            self._data[CONF_WEBHOOK_ID] = webhook.async_generate_id()
            self._data[CONF_SECRET] = secrets.token_hex(20)
        if user_input is not None:
            return self.async_create_entry(
                title=repo_name(self._data[CONF_URL]),
                data=self._data,
                options={CONF_POLL_MINUTES: 0 if self._webhook_url() else 5},
            )
        return self.async_show_form(
            step_id="webhook",
            data_schema=probatio.Schema({}),
            description_placeholders={
                "url": self._webhook_url()
                or "(Home Assistant has no external URL: GitOps checks for pushes every 5 minutes instead)",
                "secret": self._data[CONF_SECRET],
            },
        )

    def _webhook_url(self) -> str | None:
        try:
            return webhook.async_generate_url(
                self.hass, self._data[CONF_WEBHOOK_ID], allow_internal=False
            )
        except NoURLAvailableError:
            return None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """The options flow."""
        return GitOpsOptionsFlow()


class GitOpsOptionsFlow(OptionsFlow):
    """The branch, what happens after a pull, and polling."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The deploy options."""
        if user_input is not None:
            user_input[CONF_POLL_MINUTES] = int(user_input.get(CONF_POLL_MINUTES, 0))
            return self.async_create_entry(data=user_input)
        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_BRANCH,
                        default=options.get(
                            CONF_BRANCH, self.config_entry.data[CONF_BRANCH]
                        ),
                    ): TextSelector(),
                    probatio.Required(
                        CONF_RELOAD, default=options.get(CONF_RELOAD, RELOAD_ALL)
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[RELOAD_ALL, RELOAD_DOMAINS, RELOAD_NONE],
                            translation_key=CONF_RELOAD,
                        )
                    ),
                    probatio.Optional(
                        CONF_RELOAD_DOMAINS,
                        default=options.get(
                            CONF_RELOAD_DOMAINS, DEFAULT_RELOAD_DOMAINS
                        ),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=sorted(
                                d
                                for d in self.hass.services.async_services()
                                if self.hass.services.has_service(d, "reload")
                            ),
                            multiple=True,
                            custom_value=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    probatio.Required(
                        CONF_POLL_MINUTES, default=options.get(CONF_POLL_MINUTES, 0)
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=0, max=1440, step=1, mode=NumberSelectorMode.BOX
                        )
                    ),
                }
            ),
        )
