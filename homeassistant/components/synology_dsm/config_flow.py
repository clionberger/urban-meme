"""Config flow to configure the Synology DSM integration."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from synology_dsm import SynologyDSM
from synology_dsm.exceptions import (
    SynologyDSMException,
    SynologyDSMLogin2SAFailedException,
    SynologyDSMLogin2SARequiredException,
    SynologyDSMLoginInvalidException,
    SynologyDSMRequestException,
)
import voluptuous as vol

from homeassistant import exceptions
from homeassistant.components import ssdp
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import (
    CONF_DISKS,
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import DiscoveryInfoType

from .const import (
    CONF_DEVICE_TOKEN,
    CONF_VOLUMES,
    DEFAULT_PORT,
    DEFAULT_PORT_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DEFAULT_USE_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    EXCEPTION_DETAILS,
)

_LOGGER = logging.getLogger(__name__)

CONF_OTP_CODE = "otp_code"


def _discovery_schema_with_defaults(discovery_info: DiscoveryInfoType) -> vol.Schema:
    return vol.Schema(_ordered_shared_schema(discovery_info))


def _reauth_schema_with_defaults(user_input: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME, default=user_input.get(CONF_USERNAME, "")): str,
            vol.Required(CONF_PASSWORD, default=user_input.get(CONF_PASSWORD, "")): str,
        }
    )


def _user_schema_with_defaults(user_input: dict[str, Any]) -> vol.Schema:
    user_schema = {
        vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
    }
    user_schema.update(_ordered_shared_schema(user_input))

    return vol.Schema(user_schema)


def _ordered_shared_schema(
    schema_input: dict[str, Any]
) -> dict[vol.Required | vol.Optional, Any]:
    return {
        vol.Required(CONF_USERNAME, default=schema_input.get(CONF_USERNAME, "")): str,
        vol.Required(CONF_PASSWORD, default=schema_input.get(CONF_PASSWORD, "")): str,
        vol.Optional(CONF_PORT, default=schema_input.get(CONF_PORT, "")): str,
        vol.Optional(
            CONF_SSL, default=schema_input.get(CONF_SSL, DEFAULT_USE_SSL)
        ): bool,
        vol.Optional(
            CONF_VERIFY_SSL,
            default=schema_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        ): bool,
    }


class SynologyDSMFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> SynologyDSMOptionsFlowHandler:
        """Get the options flow for this handler."""
        return SynologyDSMOptionsFlowHandler(config_entry)

    def __init__(self) -> None:
        """Initialize the synology_dsm config flow."""
        self.saved_user_input: dict[str, Any] = {}
        self.discovered_conf: dict[str, Any] = {}
        self.reauth_conf: dict[str, Any] = {}
        self.reauth_reason: str | None = None

    async def _show_setup_form(
        self,
        user_input: dict[str, Any] | None = None,
        errors: dict[str, str] | None = None,
    ) -> FlowResult:
        """Show the setup form to the user."""
        if not user_input:
            user_input = {}

        description_placeholders = {}

        if self.discovered_conf:
            user_input.update(self.discovered_conf)
            step_id = "link"
            data_schema = _discovery_schema_with_defaults(user_input)
            description_placeholders = self.discovered_conf
        elif self.reauth_conf:
            user_input.update(self.reauth_conf)
            step_id = "reauth"
            data_schema = _reauth_schema_with_defaults(user_input)
            description_placeholders = {EXCEPTION_DETAILS: self.reauth_reason}
        else:
            step_id = "user"
            data_schema = _user_schema_with_defaults(user_input)

        return self.async_show_form(
            step_id=step_id,
            data_schema=data_schema,
            errors=errors or {},
            description_placeholders=description_placeholders,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is None:
            return await self._show_setup_form(user_input, None)

        if self.discovered_conf:
            user_input.update(self.discovered_conf)

        if self.reauth_conf:
            self.reauth_conf.update(
                {
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                }
            )
            user_input.update(self.reauth_conf)

        host = user_input[CONF_HOST]
        port = user_input.get(CONF_PORT)
        username = user_input[CONF_USERNAME]
        password = user_input[CONF_PASSWORD]
        use_ssl = user_input.get(CONF_SSL, DEFAULT_USE_SSL)
        verify_ssl = user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
        otp_code = user_input.get(CONF_OTP_CODE)

        if not port:
            if use_ssl is True:
                port = DEFAULT_PORT_SSL
            else:
                port = DEFAULT_PORT

        api = SynologyDSM(
            host, port, username, password, use_ssl, verify_ssl, timeout=30
        )

        try:
            serial = await self.hass.async_add_executor_job(
                _login_and_fetch_syno_info, api, otp_code
            )
        except SynologyDSMLogin2SARequiredException:
            return await self.async_step_2sa(user_input)
        except SynologyDSMLogin2SAFailedException:
            errors[CONF_OTP_CODE] = "otp_failed"
            user_input[CONF_OTP_CODE] = None
            return await self.async_step_2sa(user_input, errors)
        except SynologyDSMLoginInvalidException as ex:
            _LOGGER.error(ex)
            errors[CONF_USERNAME] = "invalid_auth"
        except SynologyDSMRequestException as ex:
            _LOGGER.error(ex)
            errors[CONF_HOST] = "cannot_connect"
        except SynologyDSMException as ex:
            _LOGGER.error(ex)
            errors["base"] = "unknown"
        except InvalidData:
            errors["base"] = "missing_data"

        if errors:
            return await self._show_setup_form(user_input, errors)

        # unique_id should be serial for services purpose
        existing_entry = await self.async_set_unique_id(serial, raise_on_progress=False)

        config_data = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_SSL: use_ssl,
            CONF_VERIFY_SSL: verify_ssl,
            CONF_USERNAME: username,
            CONF_PASSWORD: password,
            CONF_MAC: api.network.macs,
        }
        if otp_code:
            config_data[CONF_DEVICE_TOKEN] = api.device_token
        if user_input.get(CONF_DISKS):
            config_data[CONF_DISKS] = user_input[CONF_DISKS]
        if user_input.get(CONF_VOLUMES):
            config_data[CONF_VOLUMES] = user_input[CONF_VOLUMES]

        if existing_entry and self.reauth_conf:
            self.hass.config_entries.async_update_entry(
                existing_entry, data=config_data
            )
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        if existing_entry:
            return self.async_abort(reason="already_configured")

        return self.async_create_entry(title=host, data=config_data)

    async def async_step_ssdp(self, discovery_info: DiscoveryInfoType) -> FlowResult:
        """Handle a discovered synology_dsm."""
        parsed_url = urlparse(discovery_info[ssdp.ATTR_SSDP_LOCATION])
        friendly_name = (
            discovery_info[ssdp.ATTR_UPNP_FRIENDLY_NAME].split("(", 1)[0].strip()
        )

        mac = discovery_info[ssdp.ATTR_UPNP_SERIAL].upper()
        # Synology NAS can broadcast on multiple IP addresses, since they can be connected to multiple ethernets.
        # The serial of the NAS is actually its MAC address.
        if self._mac_already_configured(mac):
            return self.async_abort(reason="already_configured")

        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured()

        self.discovered_conf = {
            CONF_NAME: friendly_name,
            CONF_HOST: parsed_url.hostname,
        }
        self.context["title_placeholders"] = self.discovered_conf
        return await self.async_step_user()

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Perform reauth upon an API authentication error."""
        self.reauth_conf = self.context.get("data", {})
        self.reauth_reason = self.context.get(EXCEPTION_DETAILS)
        if user_input is None:
            return await self.async_step_user()
        return await self.async_step_user(user_input)

    async def async_step_link(self, user_input: dict[str, Any]) -> FlowResult:
        """Link a config entry from discovery."""
        return await self.async_step_user(user_input)

    async def async_step_2sa(
        self, user_input: dict[str, Any], errors: dict[str, str] | None = None
    ) -> FlowResult:
        """Enter 2SA code to anthenticate."""
        if not self.saved_user_input:
            self.saved_user_input = user_input

        if not user_input.get(CONF_OTP_CODE):
            return self.async_show_form(
                step_id="2sa",
                data_schema=vol.Schema({vol.Required(CONF_OTP_CODE): str}),
                errors=errors or {},
            )

        user_input = {**self.saved_user_input, **user_input}
        self.saved_user_input = {}

        return await self.async_step_user(user_input)

    def _mac_already_configured(self, mac: str) -> bool:
        """See if we already have configured a NAS with this MAC address."""
        existing_macs = [
            mac.replace("-", "")
            for entry in self._async_current_entries()
            for mac in entry.data.get(CONF_MAC, [])
        ]
        return mac in existing_macs


class SynologyDSMOptionsFlowHandler(OptionsFlow):
    """Handle a option flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): cv.positive_int,
                vol.Optional(
                    CONF_TIMEOUT,
                    default=self.config_entry.options.get(
                        CONF_TIMEOUT, DEFAULT_TIMEOUT
                    ),
                ): cv.positive_int,
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)


def _login_and_fetch_syno_info(api: SynologyDSM, otp_code: str) -> str:
    """Login to the NAS and fetch basic data."""
    # These do i/o
    api.login(otp_code)
    api.utilisation.update()
    api.storage.update()
    api.network.update()

    if (
        not api.information.serial
        or api.utilisation.cpu_user_load is None
        or not api.storage.volumes_ids
        or not api.network.macs
    ):
        raise InvalidData

    return api.information.serial  # type: ignore[no-any-return]


class InvalidData(exceptions.HomeAssistantError):
    """Error to indicate we get invalid data from the nas."""
