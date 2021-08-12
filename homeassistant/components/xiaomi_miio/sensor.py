"""Support for Xiaomi Mi Air Quality Monitor (PM2.5) and Humidifier."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging

from miio import AirQualityMonitor, DeviceException
from miio.gateway.gateway import (
    GATEWAY_MODEL_AC_V1,
    GATEWAY_MODEL_AC_V2,
    GATEWAY_MODEL_AC_V3,
    GATEWAY_MODEL_AQARA,
    GATEWAY_MODEL_EU,
    GatewayException,
)
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    STATE_CLASS_MEASUREMENT,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_NAME,
    CONF_TOKEN,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_TEMPERATURE,
    PERCENTAGE,
    POWER_WATT,
    PRESSURE_HPA,
    TEMP_CELSIUS,
)
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_DEVICE,
    CONF_FLOW_TYPE,
    CONF_GATEWAY,
    CONF_MODEL,
    DOMAIN,
    KEY_COORDINATOR,
    KEY_DEVICE,
    MODELS_HUMIDIFIER_MIIO,
    MODELS_HUMIDIFIER_MIOT,
    MODELS_HUMIDIFIER_MJJSQ,
)
from .device import XiaomiCoordinatedMiioEntity, XiaomiMiioEntity
from .gateway import XiaomiGatewayDevice

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Xiaomi Miio Sensor"
UNIT_LUMEN = "lm"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_TOKEN): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

ATTR_ACTUAL_MOTOR_SPEED = "actual_speed"
ATTR_AIR_QUALITY = "air_quality"
ATTR_CHARGING = "charging"
ATTR_DISPLAY_CLOCK = "display_clock"
ATTR_HUMIDITY = "humidity"
ATTR_ILLUMINANCE = "illuminance"
ATTR_LOAD_POWER = "load_power"
ATTR_NIGHT_MODE = "night_mode"
ATTR_NIGHT_TIME_BEGIN = "night_time_begin"
ATTR_NIGHT_TIME_END = "night_time_end"
ATTR_POWER = "power"
ATTR_PRESSURE = "pressure"
ATTR_SENSOR_STATE = "sensor_state"
ATTR_WATER_LEVEL = "water_level"


@dataclass
class XiaomiMiioSensorDescription(SensorEntityDescription):
    """Class that holds device specific info for a xiaomi aqara or humidifier sensor."""

    valid_min_value: float | None = None
    valid_max_value: float | None = None


SENSOR_TYPES = {
    ATTR_TEMPERATURE: XiaomiMiioSensorDescription(
        key=ATTR_TEMPERATURE,
        name="Temperature",
        unit_of_measurement=TEMP_CELSIUS,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    ATTR_HUMIDITY: XiaomiMiioSensorDescription(
        key=ATTR_HUMIDITY,
        name="Humidity",
        unit_of_measurement=PERCENTAGE,
        device_class=DEVICE_CLASS_HUMIDITY,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    ATTR_PRESSURE: XiaomiMiioSensorDescription(
        key=ATTR_PRESSURE,
        name="Pressure",
        unit_of_measurement=PRESSURE_HPA,
        device_class=DEVICE_CLASS_PRESSURE,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    ATTR_LOAD_POWER: XiaomiMiioSensorDescription(
        key=ATTR_LOAD_POWER,
        name="Load Power",
        unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
    ),
    ATTR_WATER_LEVEL: XiaomiMiioSensorDescription(
        key=ATTR_WATER_LEVEL,
        name="Water Level",
        unit_of_measurement=PERCENTAGE,
        icon="mdi:water-check",
        state_class=STATE_CLASS_MEASUREMENT,
        valid_min_value=0.0,
        valid_max_value=100.0,
    ),
    ATTR_ACTUAL_MOTOR_SPEED: XiaomiMiioSensorDescription(
        key=ATTR_ACTUAL_MOTOR_SPEED,
        name="Actual Speed",
        unit_of_measurement="rpm",
        icon="mdi:fast-forward",
        state_class=STATE_CLASS_MEASUREMENT,
        valid_min_value=200.0,
        valid_max_value=2000.0,
    ),
    ATTR_ILLUMINANCE: XiaomiMiioSensorDescription(
        key=ATTR_ILLUMINANCE,
        name="Illuminance",
        unit_of_measurement=UNIT_LUMEN,
        device_class=DEVICE_CLASS_ILLUMINANCE,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    ATTR_AIR_QUALITY: XiaomiMiioSensorDescription(
        key=ATTR_AIR_QUALITY,
        unit_of_measurement="AQI",
        icon="mdi:cloud",
        state_class=STATE_CLASS_MEASUREMENT,
    ),
}

HUMIDIFIER_MIIO_SENSORS = {
    ATTR_HUMIDITY: "humidity",
    ATTR_TEMPERATURE: "temperature",
}

HUMIDIFIER_MIOT_SENSORS = {
    ATTR_HUMIDITY: "humidity",
    ATTR_TEMPERATURE: "temperature",
    ATTR_WATER_LEVEL: "water_level",
    ATTR_ACTUAL_MOTOR_SPEED: "actual_speed",
}

HUMIDIFIER_MJJSQ_SENSORS = {
    ATTR_HUMIDITY: "humidity",
    ATTR_TEMPERATURE: "temperature",
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Import Miio configuration from YAML."""
    _LOGGER.warning(
        "Loading Xiaomi Miio Sensor via platform setup is deprecated. "
        "Please remove it from your configuration"
    )
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=config,
        )
    )


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Xiaomi sensor from a config entry."""
    entities = []

    if config_entry.data[CONF_FLOW_TYPE] == CONF_GATEWAY:
        gateway = hass.data[DOMAIN][config_entry.entry_id][CONF_GATEWAY]
        # Gateway illuminance sensor
        if gateway.model not in [
            GATEWAY_MODEL_AC_V1,
            GATEWAY_MODEL_AC_V2,
            GATEWAY_MODEL_AC_V3,
            GATEWAY_MODEL_AQARA,
            GATEWAY_MODEL_EU,
        ]:
            description = SENSOR_TYPES[ATTR_ILLUMINANCE]
            entities.append(
                XiaomiGatewayIlluminanceSensor(
                    gateway, config_entry.title, config_entry.unique_id, description
                )
            )
        # Gateway sub devices
        sub_devices = gateway.devices
        coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]
        for sub_device in sub_devices.values():
            for sensor, description in SENSOR_TYPES.items():
                if sensor not in sub_device.status:
                    continue
                entities.append(
                    XiaomiGatewaySensor(
                        coordinator, sub_device, config_entry, description
                    )
                )
    elif config_entry.data[CONF_FLOW_TYPE] == CONF_DEVICE:
        host = config_entry.data[CONF_HOST]
        token = config_entry.data[CONF_TOKEN]
        model = config_entry.data[CONF_MODEL]
        device = None
        sensors = []
        if model in MODELS_HUMIDIFIER_MIOT:
            device = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
            sensors = HUMIDIFIER_MIOT_SENSORS
        elif model in MODELS_HUMIDIFIER_MJJSQ:
            device = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
            sensors = HUMIDIFIER_MJJSQ_SENSORS
        elif model in MODELS_HUMIDIFIER_MIIO:
            device = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
            sensors = HUMIDIFIER_MIIO_SENSORS
        else:
            unique_id = config_entry.unique_id
            name = config_entry.title
            _LOGGER.debug("Initializing with host %s (token %s...)", host, token[:5])

            device = AirQualityMonitor(host, token)
            description = SENSOR_TYPES[ATTR_AIR_QUALITY]
            entities.append(
                XiaomiAirQualityMonitor(
                    name, device, config_entry, unique_id, description
                )
            )
        for sensor, description in SENSOR_TYPES.items():
            if sensor not in sensors:
                continue
            entities.append(
                XiaomiGenericSensor(
                    f"{config_entry.title} {description.name}",
                    device,
                    config_entry,
                    f"{sensor}_{config_entry.unique_id}",
                    hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR],
                    description,
                )
            )

    async_add_entities(entities)


class XiaomiGenericSensor(XiaomiCoordinatedMiioEntity, SensorEntity):
    """Representation of a Xiaomi Humidifier sensor."""

    def __init__(self, name, device, entry, unique_id, coordinator, description):
        """Initialize the entity."""
        super().__init__(name, device, entry, unique_id, coordinator)

        self._attr_name = name
        self._attr_unique_id = unique_id
        self._state = None
        self.entity_description = description

    @property
    def state(self):
        """Return the state of the device."""
        self._state = self._extract_value_from_attribute(
            self.coordinator.data, self.entity_description.key
        )
        if (
            self.entity_description.valid_min_value
            and self._state < self.entity_description.valid_min_value
        ) or (
            self.entity_description.valid_max_value
            and self._state > self.entity_description.valid_max_value
        ):
            return None
        return self._state

    @staticmethod
    def _extract_value_from_attribute(state, attribute):
        value = getattr(state, attribute)
        if isinstance(value, Enum):
            return value.value

        return value


class XiaomiAirQualityMonitor(XiaomiMiioEntity, SensorEntity):
    """Representation of a Xiaomi Air Quality Monitor."""

    def __init__(self, name, device, entry, unique_id, description):
        """Initialize the entity."""
        super().__init__(name, device, entry, unique_id)

        self._available = None
        self._state = None
        self._state_attrs = {
            ATTR_POWER: None,
            ATTR_BATTERY_LEVEL: None,
            ATTR_CHARGING: None,
            ATTR_DISPLAY_CLOCK: None,
            ATTR_NIGHT_MODE: None,
            ATTR_NIGHT_TIME_BEGIN: None,
            ATTR_NIGHT_TIME_END: None,
            ATTR_SENSOR_STATE: None,
        }
        self.entity_description = description

    @property
    def available(self):
        """Return true when state is known."""
        return self._available

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the device."""
        return self._state_attrs

    async def async_update(self):
        """Fetch state from the miio device."""
        try:
            state = await self.hass.async_add_executor_job(self._device.status)
            _LOGGER.debug("Got new state: %s", state)

            self._available = True
            self._state = state.aqi
            self._state_attrs.update(
                {
                    ATTR_POWER: state.power,
                    ATTR_CHARGING: state.usb_power,
                    ATTR_BATTERY_LEVEL: state.battery,
                    ATTR_DISPLAY_CLOCK: state.display_clock,
                    ATTR_NIGHT_MODE: state.night_mode,
                    ATTR_NIGHT_TIME_BEGIN: state.night_time_begin,
                    ATTR_NIGHT_TIME_END: state.night_time_end,
                    ATTR_SENSOR_STATE: state.sensor_state,
                }
            )

        except DeviceException as ex:
            if self._available:
                self._available = False
                _LOGGER.error("Got exception while fetching the state: %s", ex)


class XiaomiGatewaySensor(XiaomiGatewayDevice, SensorEntity):
    """Representation of a XiaomiGatewaySensor."""

    def __init__(self, coordinator, sub_device, entry, description):
        """Initialize the XiaomiSensor."""
        super().__init__(coordinator, sub_device, entry)
        self._unique_id = f"{sub_device.sid}-{description.key}"
        self._name = f"{description.key} ({sub_device.sid})".capitalize()
        self.entity_description = description

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._sub_device.status[self.entity_description.key]


class XiaomiGatewayIlluminanceSensor(SensorEntity):
    """Representation of the gateway device's illuminance sensor."""

    def __init__(self, gateway_device, gateway_name, gateway_device_id, description):
        """Initialize the entity."""

        self._attr_name = f"{gateway_name} {description.name}"
        self._attr_unique_id = f"{gateway_device_id}-{description.key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, gateway_device_id)}}
        self._gateway = gateway_device
        self.entity_description = description
        self._available = False
        self._state = None

    @property
    def available(self):
        """Return true when state is known."""
        return self._available

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    async def async_update(self):
        """Fetch state from the device."""
        try:
            self._state = await self.hass.async_add_executor_job(
                self._gateway.get_illumination
            )
            self._available = True
        except GatewayException as ex:
            if self._available:
                self._available = False
                _LOGGER.error(
                    "Got exception while fetching the gateway illuminance state: %s", ex
                )
