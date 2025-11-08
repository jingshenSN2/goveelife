"""Sensor entities for the Govee Life integration."""

from __future__ import annotations
from typing import Final
import logging
import asyncio
import re

from homeassistant.core import (
    HomeAssistant,
    callback,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorStateClass
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import (
    CONF_DEVICES,
    STATE_UNKNOWN,
    CONF_STATE,
    UnitOfTemperature,
    PERCENTAGE,
    CONCENTRATION_PARTS_PER_MILLION,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)

from .entities import GoveeLifePlatformEntity
from .utils import GoveeAPI_GetCachedStateValue

from .const import (
    DOMAIN,
    CONF_COORDINATORS,
)
from .utils import (
    async_ProgrammingDebug,
)

_LOGGER: Final = logging.getLogger(__name__)
platform='sensor'
platform_device_types = [
    'devices.types.sensor:.*',
    'devices.types.thermometer:.*',
    'devices.types.air_quality_monitor:.*'
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the sensor platform."""
    _LOGGER.debug("Setting up %s platform entry: %s | %s", platform, DOMAIN, entry.entry_id)
    entites=[]
    
    
    try:
        _LOGGER.debug("%s - async_setup_entry %s: Getting cloud devices from data store", entry.entry_id, platform)
        entry_data=hass.data[DOMAIN][entry.entry_id]
        api_devices=entry_data[CONF_DEVICES]
    except Exception as e:
        _LOGGER.error("%s - async_setup_entry %s: Getting cloud devices from data store failed: %s (%s.%s)", entry.entry_id, platform, str(e), e.__class__.__module__, type(e).__name__)
        return False

    for device_cfg in api_devices:
        try:
            d=device_cfg.get('device')
            coordinator = entry_data[CONF_COORDINATORS][d]
            for capability in device_cfg.get('capabilities',[]):
                r=device_cfg.get('type',STATE_UNKNOWN)+':'+capability.get('type',STATE_UNKNOWN)+':'+capability.get('instance',STATE_UNKNOWN)
                setup=False
                for platform_match in platform_device_types:
                    if re.match(platform_match, r):
                        setup=True
                        break
                if setup:
                    _LOGGER.debug("%s - async_setup_entry %s: Setup capability: %s|%s|%s ", entry.entry_id, platform, d, capability.get('type',STATE_UNKNOWN).split('.')[-1], capability.get('instance',STATE_UNKNOWN))
                    entity=GoveeLifeSensor(hass, entry, coordinator, device_cfg, platform=platform, cap=capability)
                    entites.append(entity)
            await asyncio.sleep(0)
        except Exception as e:
            _LOGGER.error("%s - async_setup_entry %s: Setup device failed: %s (%s.%s)", entry.entry_id, platform, str(e), e.__class__.__module__, type(e).__name__)
            return False

    _LOGGER.info("%s - async_setup_entry: setup %s %s entities", entry.entry_id, len(entites), platform)
    if not entites:
        return None
    async_add_entities(entites)


class GoveeLifeSensor(GoveeLifePlatformEntity):
    """Sensor class for Govee Life integration."""

    def _init_platform_specific(self, **kwargs):
        """Platform specific init actions"""
        capabilities = kwargs.get('cap')
        self._capability_name = capabilities.get('instance')
        self.uniqueid = self._identifier + '_' + self._entity_id + '_' + self._capability_name
        self._name = self._capability_name
        self._state_class = SensorStateClass.MEASUREMENT

        # Map capability instance to device class and unit of measurement
        self._device_class = None
        self._unit_of_measurement = None

        # Temperature sensors
        if self._capability_name in ['sensorTemperature', 'temperature']:
            self._device_class = SensorDeviceClass.TEMPERATURE
            self._unit_of_measurement = UnitOfTemperature.CELSIUS

        # Humidity sensors
        elif self._capability_name in ['sensorHumidity', 'humidity']:
            self._device_class = SensorDeviceClass.HUMIDITY
            self._unit_of_measurement = PERCENTAGE

        # CO2 sensors
        elif self._capability_name in ['carbonDioxideConcentration', 'co2']:
            self._device_class = SensorDeviceClass.CO2
            self._unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION

    @property
    def state_class(self) -> SensorStateClass | None:
        """Return the state_class of the entity."""
        _LOGGER.debug("%s - %s: state_class: property requested", self._api_id, self._identifier)
        return self._state_class

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Return the device_class of the entity."""
        return self._device_class

    @property
    def unit_of_measurement(self) -> str | None:
        """Return the unit_of_measurement of the entity."""
        return self._unit_of_measurement

    @property
    def capability_attributes(self):
        if not self.state_class is None:
            return {"state_class": self.state_class}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        #self._attr_is_on = self.coordinator.data[self.idx]["state"]        
        d=self._device_cfg.get('device')
        self.hass.data[DOMAIN][self._entry_id][CONF_STATE][d]
        self.async_write_ha_state()
 
    @property
    def state(self) -> str | None:
        """Return the current state of the entity."""
        value = GoveeAPI_GetCachedStateValue(self.hass, self._entry_id, self._device_cfg.get('device'), 'devices.capabilities.property', self._capability_name)
        _LOGGER.debug("%s - %s: state value: %s", self._api_id, self._identifier, value)
        return value
        

