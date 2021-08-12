"""Test the Uptime Robot config flow."""
from unittest.mock import patch

from homeassistant import config_entries, setup
from homeassistant.components.uptimerobot.const import (
    API_ATTR_MONITORS,
    API_ATTR_OK,
    API_ATTR_STAT,
    DOMAIN,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import (
    RESULT_TYPE_ABORT,
    RESULT_TYPE_CREATE_ENTRY,
    RESULT_TYPE_FORM,
)


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] == {}

    with patch(
        "pyuptimerobot.UptimeRobot.getMonitors",
        return_value={API_ATTR_STAT: API_ATTR_OK, API_ATTR_MONITORS: []},
    ), patch(
        "homeassistant.components.uptimerobot.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"api_key": "1234"},
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == ""
    assert result2["data"] == {"api_key": "1234"}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("pyuptimerobot.UptimeRobot.getMonitors", return_value=None):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"api_key": "1234"},
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_flow_import(hass):
    """Test an import flow."""
    with patch(
        "pyuptimerobot.UptimeRobot.getMonitors",
        return_value={API_ATTR_STAT: API_ATTR_OK, API_ATTR_MONITORS: []},
    ), patch(
        "homeassistant.components.uptimerobot.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={"platform": DOMAIN, "api_key": "1234"},
        )
        await hass.async_block_till_done()

        assert len(mock_setup_entry.mock_calls) == 1
        assert result["type"] == RESULT_TYPE_CREATE_ENTRY
        assert result["data"] == {"api_key": "1234"}

    with patch(
        "pyuptimerobot.UptimeRobot.getMonitors",
        return_value={API_ATTR_STAT: API_ATTR_OK, API_ATTR_MONITORS: []},
    ), patch(
        "homeassistant.components.uptimerobot.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={"platform": DOMAIN, "api_key": "1234"},
        )
        await hass.async_block_till_done()

        assert result["type"] == RESULT_TYPE_ABORT
        assert result["reason"] == "already_configured"
