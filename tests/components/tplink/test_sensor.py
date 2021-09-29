"""Tests for light platform."""

from unittest.mock import Mock

from homeassistant.components import tplink
from homeassistant.components.tplink.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from . import (
    MAC_ADDRESS,
    _mocked_bulb,
    _mocked_plug,
    _patch_discovery,
    _patch_single_discovery,
)

from tests.common import MockConfigEntry


async def test_color_light_with_an_emeter(hass: HomeAssistant) -> None:
    """Test a light with an emeter."""
    already_migrated_config_entry = MockConfigEntry(
        domain=DOMAIN, data={}, unique_id=MAC_ADDRESS
    )
    already_migrated_config_entry.add_to_hass(hass)
    bulb = _mocked_bulb()
    bulb.color_temp = None
    bulb.has_emeter = True
    bulb.emeter_realtime = Mock(
        power=None,
        total=None,
        voltage=None,
        current=5,
    )
    bulb.emeter_today = 5000
    with _patch_discovery(device=bulb), _patch_single_discovery(device=bulb):
        await async_setup_component(hass, tplink.DOMAIN, {tplink.DOMAIN: {}})
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    expected = {
        "sensor.my_bulb_today_s_consumption": 5000,
        "sensor.my_bulb_current": 5,
    }
    entity_id = "light.my_bulb"
    state = hass.states.get(entity_id)
    assert state.state == "on"
    for sensor_entity_id, value in expected.items():
        assert hass.states.get(sensor_entity_id).state == str(value)

    not_expected = {
        "sensor.my_bulb_current_consumption",
        "sensor.my_bulb_total_consumption",
        "sensor.my_bulb_voltage",
    }
    for sensor_entity_id in not_expected:
        assert hass.states.get(sensor_entity_id) is None


async def test_plug_with_an_emeter(hass: HomeAssistant) -> None:
    """Test a plug with an emeter."""
    already_migrated_config_entry = MockConfigEntry(
        domain=DOMAIN, data={}, unique_id=MAC_ADDRESS
    )
    already_migrated_config_entry.add_to_hass(hass)
    plug = _mocked_plug()
    plug.color_temp = None
    plug.has_emeter = True
    plug.emeter_realtime = Mock(
        power=100,
        total=30,
        voltage=121,
        current=5,
    )
    plug.emeter_today = None
    with _patch_discovery(device=plug), _patch_single_discovery(device=plug):
        await async_setup_component(hass, tplink.DOMAIN, {tplink.DOMAIN: {}})
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    expected = {
        "sensor.my_plug_current_consumption": 100,
        "sensor.my_plug_total_consumption": 30,
        "sensor.my_plug_today_s_consumption": 0.0,
        "sensor.my_plug_voltage": 121,
        "sensor.my_plug_current": 5,
    }
    entity_id = "switch.my_plug"
    state = hass.states.get(entity_id)
    assert state.state == "on"
    for sensor_entity_id, value in expected.items():
        assert hass.states.get(sensor_entity_id).state == str(value)


async def test_color_light_no_emeter(hass: HomeAssistant) -> None:
    """Test a light without an emeter."""
    already_migrated_config_entry = MockConfigEntry(
        domain=DOMAIN, data={}, unique_id=MAC_ADDRESS
    )
    already_migrated_config_entry.add_to_hass(hass)
    bulb = _mocked_bulb()
    bulb.color_temp = None
    bulb.has_emeter = False
    with _patch_discovery(device=bulb), _patch_single_discovery(device=bulb):
        await async_setup_component(hass, tplink.DOMAIN, {tplink.DOMAIN: {}})
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    entity_id = "light.my_bulb"
    state = hass.states.get(entity_id)
    assert state.state == "on"

    not_expected = [
        "sensor.my_bulb_current_consumption"
        "sensor.my_bulb_total_consumption"
        "sensor.my_bulb_today_s_consumption"
        "sensor.my_bulb_voltage"
        "sensor.my_bulb_current"
    ]
    for sensor_entity_id in not_expected:
        assert hass.states.get(sensor_entity_id) is None
