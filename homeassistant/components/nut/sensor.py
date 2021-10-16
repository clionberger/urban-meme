"""Provides a sensor to track various status aspects of a UPS."""
from __future__ import annotations

import logging

from homeassistant.components.nut import PyNUTData
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import CONF_RESOURCES, STATE_UNKNOWN
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    COORDINATOR,
    DOMAIN,
    KEY_STATUS,
    KEY_STATUS_DISPLAY,
    PYNUT_DATA,
    PYNUT_FIRMWARE,
    PYNUT_MANUFACTURER,
    PYNUT_MODEL,
    PYNUT_UNIQUE_ID,
    SENSOR_TYPES,
    STATE_TYPES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the NUT sensors."""

    pynut_data = hass.data[DOMAIN][config_entry.entry_id]
    unique_id = pynut_data[PYNUT_UNIQUE_ID]
    manufacturer = pynut_data[PYNUT_MANUFACTURER]
    model = pynut_data[PYNUT_MODEL]
    firmware = pynut_data[PYNUT_FIRMWARE]
    coordinator = pynut_data[COORDINATOR]
    data = pynut_data[PYNUT_DATA]
    status = coordinator.data

    enabled_resources = [
        resource.lower() for resource in config_entry.data[CONF_RESOURCES]
    ]
    resources = [sensor_id for sensor_id in SENSOR_TYPES if sensor_id in status]
    # Display status is a special case that falls back to the status value
    # of the UPS instead.
    if KEY_STATUS in resources:
        resources.append(KEY_STATUS_DISPLAY)

    entities = [
        NUTSensor(
            coordinator,
            data,
            SENSOR_TYPES[sensor_type],
            unique_id,
            manufacturer,
            model,
            firmware,
            sensor_type in enabled_resources,
        )
        for sensor_type in resources
    ]

    async_add_entities(entities, True)


class NUTSensor(CoordinatorEntity, SensorEntity):
    """Representation of a sensor entity for NUT status values."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        data: PyNUTData,
        sensor_description: SensorEntityDescription,
        unique_id: str,
        manufacturer: str | None,
        model: str | None,
        firmware: str | None,
        enabled_default: bool,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = sensor_description
        self._manufacturer = manufacturer
        self._firmware = firmware
        self._model = model
        self._device_name = data.name.title()
        self._unique_id = unique_id

        self._attr_entity_registry_enabled_default = enabled_default
        self._attr_name = f"{self._device_name} {sensor_description.name}"
        self._attr_unique_id = f"{unique_id}_{sensor_description.key}"

    @property
    def device_info(self):
        """Device info for the ups."""
        device_info = {
            "identifiers": {(DOMAIN, self._unique_id)},
            "name": self._device_name,
        }
        if self._model:
            device_info["model"] = self._model
        if self._manufacturer:
            device_info["manufacturer"] = self._manufacturer
        if self._firmware:
            device_info["sw_version"] = self._firmware
        return device_info

    @property
    def native_value(self):
        """Return entity state from ups."""
        status = self.coordinator.data
        if self.entity_description.key == KEY_STATUS_DISPLAY:
            return _format_display_state(status)
        return status.get(self.entity_description.key)


def _format_display_state(status):
    """Return UPS display state."""
    try:
        return " ".join(STATE_TYPES[state] for state in status[KEY_STATUS].split())
    except KeyError:
        return STATE_UNKNOWN
