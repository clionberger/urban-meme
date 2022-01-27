"""Binary sensor for Shelly."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, cast

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import RegistryEntry

from .const import CONF_SLEEP_PERIOD
from .entity import (
    BlockEntityDescription,
    RestEntityDescription,
    RpcEntityDescription,
    ShellyBlockAttributeEntity,
    ShellyRestAttributeEntity,
    ShellyRpcAttributeEntity,
    ShellySleepingBlockAttributeEntity,
    async_setup_entry_attribute_entities,
    async_setup_entry_rest,
    async_setup_entry_rpc,
)
from .utils import (
    get_device_entry_gen,
    is_block_momentary_input,
    is_rpc_momentary_input,
)


@dataclass
class BlockBinarySensorDescription(
    BlockEntityDescription, BinarySensorEntityDescription
):
    """Class to describe a BLOCK binary sensor."""


@dataclass
class RpcBinarySensorDescription(RpcEntityDescription, BinarySensorEntityDescription):
    """Class to describe a RPC binary sensor."""


@dataclass
class RestBinarySensorDescription(RestEntityDescription, BinarySensorEntityDescription):
    """Class to describe a REST binary sensor."""


SENSORS: Final = {
    ("device", "overtemp"): BlockBinarySensorDescription(
        key="device|overtemp",
        name="Overheating",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ("device", "overpower"): BlockBinarySensorDescription(
        key="device|overpower",
        name="Overpowering",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ("light", "overpower"): BlockBinarySensorDescription(
        key="light|overpower",
        name="Overpowering",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ("relay", "overpower"): BlockBinarySensorDescription(
        key="relay|overpower",
        name="Overpowering",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ("sensor", "dwIsOpened"): BlockBinarySensorDescription(
        key="sensor|dwIsOpened",
        name="Door",
        device_class=BinarySensorDeviceClass.OPENING,
        available=lambda block: cast(int, block.dwIsOpened) != -1,
    ),
    ("sensor", "flood"): BlockBinarySensorDescription(
        key="sensor|flood", name="Flood", device_class=BinarySensorDeviceClass.MOISTURE
    ),
    ("sensor", "gas"): BlockBinarySensorDescription(
        key="sensor|gas",
        name="Gas",
        device_class=BinarySensorDeviceClass.GAS,
        value=lambda value: value in ["mild", "heavy"],
        extra_state_attributes=lambda block: {"detected": block.gas},
    ),
    ("sensor", "smoke"): BlockBinarySensorDescription(
        key="sensor|smoke", name="Smoke", device_class=BinarySensorDeviceClass.SMOKE
    ),
    ("sensor", "vibration"): BlockBinarySensorDescription(
        key="sensor|vibration",
        name="Vibration",
        device_class=BinarySensorDeviceClass.VIBRATION,
    ),
    ("input", "input"): BlockBinarySensorDescription(
        key="input|input",
        name="Input",
        device_class=BinarySensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
        removal_condition=is_block_momentary_input,
    ),
    ("relay", "input"): BlockBinarySensorDescription(
        key="relay|input",
        name="Input",
        device_class=BinarySensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
        removal_condition=is_block_momentary_input,
    ),
    ("device", "input"): BlockBinarySensorDescription(
        key="device|input",
        name="Input",
        device_class=BinarySensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
        removal_condition=is_block_momentary_input,
    ),
    ("sensor", "extInput"): BlockBinarySensorDescription(
        key="sensor|extInput",
        name="External Input",
        device_class=BinarySensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    ("sensor", "motion"): BlockBinarySensorDescription(
        key="sensor|motion", name="Motion", device_class=BinarySensorDeviceClass.MOTION
    ),
}

REST_SENSORS: Final = {
    "cloud": RestBinarySensorDescription(
        key="cloud",
        name="Cloud",
        value=lambda status, _: status["cloud"]["connected"],
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "fwupdate": RestBinarySensorDescription(
        key="fwupdate",
        name="Firmware Update",
        device_class=BinarySensorDeviceClass.UPDATE,
        value=lambda status, _: status["update"]["has_update"],
        entity_registry_enabled_default=False,
        extra_state_attributes=lambda status: {
            "latest_stable_version": status["update"]["new_version"],
            "installed_version": status["update"]["old_version"],
            "beta_version": status["update"].get("beta_version", ""),
        },
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}

RPC_SENSORS: Final = {
    "input": RpcBinarySensorDescription(
        key="input",
        sub_key="state",
        name="Input",
        device_class=BinarySensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
        removal_condition=is_rpc_momentary_input,
    ),
    "cloud": RpcBinarySensorDescription(
        key="cloud",
        sub_key="connected",
        name="Cloud",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "fwupdate": RpcBinarySensorDescription(
        key="sys",
        sub_key="available_updates",
        name="Firmware Update",
        device_class=BinarySensorDeviceClass.UPDATE,
        entity_registry_enabled_default=False,
        extra_state_attributes=lambda status, shelly: {
            "latest_stable_version": status.get("stable", {"version": ""})["version"],
            "installed_version": shelly["ver"],
            "beta_version": status.get("beta", {"version": ""})["version"],
        },
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}


def _build_block_description(entry: RegistryEntry) -> BlockBinarySensorDescription:
    """Build description when restoring block attribute entities."""
    return BlockBinarySensorDescription(
        key="",
        name="",
        icon=entry.original_icon,
        device_class=entry.original_device_class,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for device."""
    if get_device_entry_gen(config_entry) == 2:
        return await async_setup_entry_rpc(
            hass, config_entry, async_add_entities, RPC_SENSORS, RpcBinarySensor
        )

    if config_entry.data[CONF_SLEEP_PERIOD]:
        await async_setup_entry_attribute_entities(
            hass,
            config_entry,
            async_add_entities,
            SENSORS,
            BlockSleepingBinarySensor,
            _build_block_description,
        )
    else:
        await async_setup_entry_attribute_entities(
            hass,
            config_entry,
            async_add_entities,
            SENSORS,
            BlockBinarySensor,
            _build_block_description,
        )
        await async_setup_entry_rest(
            hass,
            config_entry,
            async_add_entities,
            REST_SENSORS,
            RestBinarySensor,
        )


class BlockBinarySensor(ShellyBlockAttributeEntity, BinarySensorEntity):
    """Represent a block binary sensor entity."""

    entity_description: BlockBinarySensorDescription

    @property
    def is_on(self) -> bool:
        """Return true if sensor state is on."""
        return bool(self.attribute_value)


class RestBinarySensor(ShellyRestAttributeEntity, BinarySensorEntity):
    """Represent a REST binary sensor entity."""

    entity_description: RestBinarySensorDescription

    @property
    def is_on(self) -> bool | None:
        """Return true if REST sensor state is on."""
        if self.attribute_value is None:
            return None
        return bool(self.attribute_value)


class RpcBinarySensor(ShellyRpcAttributeEntity, BinarySensorEntity):
    """Represent a RPC binary sensor entity."""

    entity_description: RpcBinarySensorDescription

    @property
    def is_on(self) -> bool | None:
        """Return true if RPC sensor state is on."""
        if self.attribute_value is None:
            return None
        return bool(self.attribute_value)


class BlockSleepingBinarySensor(ShellySleepingBlockAttributeEntity, BinarySensorEntity):
    """Represent a block sleeping binary sensor."""

    entity_description: BlockBinarySensorDescription

    @property
    def is_on(self) -> bool:
        """Return true if sensor state is on."""
        if self.block is not None:
            return bool(self.attribute_value)

        return self.last_state == STATE_ON
