# Support for SMA Energy Meter.
# Copyright (c) 2026 transistorgrab@github.com 
# Licensed under the MIT License

from homeassistant.components.sensor import (
                                SensorEntity
                                ,SensorDeviceClass
                                ,SensorStateClass
                                )
from homeassistant.helpers.entity import DeviceInfo
from . import DOMAIN
import logging
_LOGGER = logging.getLogger(__name__)

SENSORS = {
     "power import"      : ("Emeter Import Power", "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)
    ,"power export"      : ("Emeter Export Power", "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)
    ,"power netto"       : ("Emeter Net Power",    "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)
    ,"power L1"          : ("Emeter L1 Power",     "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)
    ,"power L2"          : ("Emeter L2 Power",     "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)
    ,"power L3"          : ("Emeter L3 Power",     "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)

    ,"energy imported"   : ("Emeter Imported Energy", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)
    ,"energy exported"   : ("Emeter Exported Energy", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)

    ,"energy L1 imported": ("Emeter L1 Imported Energy", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)
    ,"energy L2 imported": ("Emeter L2 Imported Energy", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)
    ,"energy L3 imported": ("Emeter L3 Imported Energy", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)

    ,"energy L1 exported": ("Emeter L1 Exported Energy", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)
    ,"energy L2 exported": ("Emeter L2 Exported Energy", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)
    ,"energy L3 exported": ("Emeter L3 Exported Energy", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)
}
async def async_setup_entry(hass, entry, async_add_entities):
    listener = hass.data[DOMAIN][entry.entry_id]
    serial_number = entry.data.get('serial_number')
    _LOGGER.info(f"Setting up SMA EMeter {serial_number} sensors")

    entities = [
        SMAEmeterSensor(listener, key, name, unit, d_class, s_class, serial_number)
        for key, (name, unit, d_class, s_class) in SENSORS.items()
        ]

    hass.data.setdefault("sma_emeter_entities", []).extend(entities)
    async_add_entities(entities)

class SMAEmeterSensor(SensorEntity):
    def __init__(self, listener, key, name, unit, d_class, s_class, serial_number):
        self.listener                         = listener
        self.key                              = key
        self.serial_number                    = serial_number
        self._attr_name                       = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class               = d_class
        self._attr_state_class                = s_class
        self._attr_unique_id                  = f"{DOMAIN}_{self.serial_number}_{key.replace(' ','_')}"  # make it customizable
        self._attr_should_poll                = False  # we push our values
        # group sensors to specific device
        self._attr_device_info = DeviceInfo(
                    identifiers={(DOMAIN, self.serial_number)}
                    ,name=f"SMA Energy Meter ({self.serial_number})"
                    ,manufacturer='SMA Solar Technology'
                    ,model="SMA Energy Meter"
                    )
    @property
    def native_value(self):
        meter_data = self.listener.data.get(self.serial_number,{})
        return meter_data.get(self.key)
