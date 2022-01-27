"""Aussie Broadband sensor platform tests."""
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN

from .common import setup_platform

MOCK_NBN_USAGE = {
    "usedMb": 54321,
    "downloadedMb": 50000,
    "uploadedMb": 4321,
    "daysTotal": 28,
    "daysRemaining": 25,
}

MOCK_MOBILE_USAGE = {
    "national": {"calls": 1, "cost": 0},
    "mobile": {"calls": 2, "cost": 0},
    "international": {"calls": 3, "cost": 0},
    "sms": {"calls": 4, "cost": 0},
    "internet": {"kbytes": 512, "cost": 0},
    "voicemail": {"calls": 6, "cost": 0},
    "other": {"calls": 7, "cost": 0},
    "daysTotal": 31,
    "daysRemaining": 30,
    "historical": [],
}


async def test_nbn_sensor_states(hass):
    """Tests that the sensors are correct."""

    await setup_platform(hass, [SENSOR_DOMAIN], usage=MOCK_NBN_USAGE)

    assert hass.states.get("sensor.nbn_data_used").state == "54321"
    assert hass.states.get("sensor.nbn_downloaded").state == "50000"
    assert hass.states.get("sensor.nbn_uploaded").state == "4321"
    assert hass.states.get("sensor.nbn_billing_cycle_length").state == "28"
    assert hass.states.get("sensor.nbn_billing_cycle_remaining").state == "25"


async def test_phone_sensor_states(hass):
    """Tests that the sensors are correct."""

    await setup_platform(hass, [SENSOR_DOMAIN], usage=MOCK_MOBILE_USAGE)

    assert hass.states.get("sensor.mobile_national_calls").state == "1"
    assert hass.states.get("sensor.mobile_mobile_calls").state == "2"
    assert hass.states.get("sensor.mobile_sms_sent").state == "4"
    assert hass.states.get("sensor.mobile_data_used").state == "512"
    assert hass.states.get("sensor.mobile_billing_cycle_length").state == "31"
    assert hass.states.get("sensor.mobile_billing_cycle_remaining").state == "30"
