"""Configuration for Sonos tests."""
from unittest.mock import AsyncMock, MagicMock, Mock, patch as patch

import pytest

from homeassistant.components.media_player import DOMAIN as MP_DOMAIN
from homeassistant.components.sonos import DOMAIN
from homeassistant.const import CONF_HOSTS

from tests.common import MockConfigEntry


class SonosMockEvent:
    """Mock a sonos Event used in callbacks."""

    def __init__(self, soco, variables):
        """Initialize the instance."""
        self.sid = f"{soco.uid}_sub0000000001"
        self.seq = "0"
        self.timestamp = 1621000000.0
        self.service = dummy_soco_service_fixture
        self.variables = variables


@pytest.fixture(name="config_entry")
def config_entry_fixture():
    """Create a mock Sonos config entry."""
    return MockConfigEntry(domain=DOMAIN, title="Sonos")


@pytest.fixture(name="soco")
def soco_fixture(
    music_library, speaker_info, battery_info, dummy_soco_service, alarm_clock
):
    """Create a mock pysonos SoCo fixture."""
    with patch("pysonos.SoCo", autospec=True) as mock, patch(
        "socket.gethostbyname", return_value="192.168.42.2"
    ):
        mock_soco = mock.return_value
        mock_soco.uid = "RINCON_test"
        mock_soco.play_mode = "NORMAL"
        mock_soco.music_library = music_library
        mock_soco.get_speaker_info.return_value = speaker_info
        mock_soco.avTransport = dummy_soco_service
        mock_soco.renderingControl = dummy_soco_service
        mock_soco.zoneGroupTopology = dummy_soco_service
        mock_soco.contentDirectory = dummy_soco_service
        mock_soco.deviceProperties = dummy_soco_service
        mock_soco.alarmClock = alarm_clock
        mock_soco.mute = False
        mock_soco.night_mode = True
        mock_soco.dialog_mode = True
        mock_soco.volume = 19
        mock_soco.get_battery_info.return_value = battery_info
        mock_soco.all_zones = [mock_soco]
        yield mock_soco


@pytest.fixture(name="discover", autouse=True)
def discover_fixture(soco):
    """Create a mock pysonos discover fixture."""

    def do_callback(callback, **kwargs):
        callback(soco)
        return MagicMock()

    with patch("pysonos.discover_thread", side_effect=do_callback) as mock:
        yield mock


@pytest.fixture(name="config")
def config_fixture():
    """Create hass config fixture."""
    return {DOMAIN: {MP_DOMAIN: {CONF_HOSTS: ["192.168.42.1"]}}}


@pytest.fixture(name="dummy_soco_service")
def dummy_soco_service_fixture():
    """Create dummy_soco_service fixture."""
    service = Mock()
    service.subscribe = AsyncMock()
    return service


@pytest.fixture(name="music_library")
def music_library_fixture():
    """Create music_library fixture."""
    music_library = Mock()
    music_library.get_sonos_favorites.return_value = []
    return music_library


@pytest.fixture(name="alarm_clock")
def alarm_clock_fixture():
    """Create alarmClock fixture."""
    alarm_clock = Mock()
    alarm_clock.subscribe = AsyncMock()
    alarm_clock.ListAlarms.return_value = {
        "CurrentAlarmList": "<Alarms>"
        '<Alarm ID="14" StartTime="07:00:00" Duration="02:00:00" Recurrence="DAILY" '
        'Enabled="1" RoomUUID="RINCON_test" ProgramURI="x-rincon-buzzer:0" '
        'ProgramMetaData="" PlayMode="SHUFFLE_NOREPEAT" Volume="25" '
        'IncludeLinkedZones="0"/>'
        "</Alarms> "
    }
    return alarm_clock


@pytest.fixture(name="alarm_clock_extended")
def alarm_clock_fixture_extended():
    """Create alarmClock fixture."""
    alarm_clock = Mock()
    alarm_clock.subscribe = AsyncMock()
    alarm_clock.ListAlarms.return_value = {
        "CurrentAlarmList": "<Alarms>"
        '<Alarm ID="14" StartTime="07:00:00" Duration="02:00:00" Recurrence="DAILY" '
        'Enabled="1" RoomUUID="RINCON_test" ProgramURI="x-rincon-buzzer:0" '
        'ProgramMetaData="" PlayMode="SHUFFLE_NOREPEAT" Volume="25" '
        'IncludeLinkedZones="0"/>'
        '<Alarm ID="15" StartTime="07:00:00" Duration="02:00:00" '
        'Recurrence="DAILY" Enabled="1" RoomUUID="RINCON_test" '
        'ProgramURI="x-rincon-buzzer:0" ProgramMetaData="" PlayMode="SHUFFLE_NOREPEAT" '
        'Volume="25" IncludeLinkedZones="0"/>'
        "</Alarms> "
    }
    return alarm_clock


@pytest.fixture(name="speaker_info")
def speaker_info_fixture():
    """Create speaker_info fixture."""
    return {
        "zone_name": "Zone A",
        "model_name": "Model Name",
        "software_version": "49.2-64250",
        "mac_address": "00-11-22-33-44-55",
        "display_version": "13.1",
    }


@pytest.fixture(name="battery_info")
def battery_info_fixture():
    """Create battery_info fixture."""
    return {
        "Health": "GREEN",
        "Level": 100,
        "Temperature": "NORMAL",
        "PowerSource": "SONOS_CHARGING_RING",
    }


@pytest.fixture(name="battery_event")
def battery_event_fixture(soco):
    """Create battery_event fixture."""
    variables = {
        "zone_name": "Zone A",
        "more_info": "BattChg:NOT_CHARGING,RawBattPct:100,BattPct:100,BattTmp:25",
    }
    return SonosMockEvent(soco, variables)


@pytest.fixture(name="alarm_event")
def alarm_event_fixture(soco):
    """Create alarm_event fixture."""
    variables = {
        "time_zone": "ffc40a000503000003000502ffc4",
        "time_server": "0.sonostime.pool.ntp.org,1.sonostime.pool.ntp.org,2.sonostime.pool.ntp.org,3.sonostime.pool.ntp.org",
        "time_generation": "20000001",
        "alarm_list_version": "RINCON_test",
        "time_format": "INV",
        "date_format": "INV",
        "daily_index_refresh_time": None,
    }

    return SonosMockEvent(soco, variables)
