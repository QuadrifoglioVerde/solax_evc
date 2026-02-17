import logging
import async_timeout
import aiohttp
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorEntity, 
    SensorDeviceClass, 
    SensorStateClass
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import (
    UnitOfEnergy, 
    UnitOfPower, 
    UnitOfElectricCurrent, 
    UnitOfElectricPotential, 
    UnitOfTemperature, 
    UnitOfTime
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=60)

# Definice podle vaseho JSONu: (Název, Index, Jednotka, DeviceClass, Koeficient)
SENSOR_TYPES = [
    ("Device State", 0, None, None, "STATE"),
    ("Device Mode", 1, None, None, "MODE"),
    ("Voltage A", 3, UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, 0.01),
    ("Voltage B", 4, UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, 0.01),
    ("Voltage C", 5, UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, 0.01),
    ("Current A", 6, UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, 0.01),
    ("Current B", 7, UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, 0.01),
    ("Current C", 8, UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, 0.01),
    ("Power A", 9, UnitOfPower.WATT, SensorDeviceClass.POWER, 1),
    ("Power B", 10, UnitOfPower.WATT, SensorDeviceClass.POWER, 1),
    ("Power C", 11, UnitOfPower.WATT, SensorDeviceClass.POWER, 1),
    ("Total Power", 12, UnitOfPower.WATT, SensorDeviceClass.POWER, 1),
    ("EQ Single", 13, UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, 0.1),
    ("EQ Total", 15, UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, 0.1),
    ("Temperature PCB", 24, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, 1),
]

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    host = config.get("host")
    pwd = config.get("password")
    session = async_get_clientsession(hass)
    
    entities = []
    for info in SENSOR_TYPES:
        entities.append(SolaxEVCSensor(host, pwd, info, session))
        
    async_add_entities(entities, update_before_add=True)

class SolaxEVCSensor(SensorEntity):
    def __init__(self, host, pwd, info, session):
        self._host = host
        self._pwd = pwd
        self._name_suffix, self._index, self._unit, self._device_class, self._factor = info
        self._session = session
        self._attr_name = f"SolaX EVC {self._name_suffix}"
        # Změna unique_id na název, aby se při změně indexu entity nepomíchaly
        clean_name = self._name_suffix.lower().replace(" ", "_")
        self._attr_unique_id = f"solax_evc_{host}_{clean_name}"
        self._attr_native_unit_of_measurement = self._unit
        self._attr_device_class = self._device_class
        self._state = None
        
        if self._device_class == SensorDeviceClass.ENERGY:
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        return self._state

    async def async_update(self):
        url = f"http://{self._host}"
        payload = f"optType=ReadRealTimeData&pwd={self._pwd}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            async with async_timeout.timeout(10):
                async with self._session.post(url, data=payload, headers=headers) as response:
                    res = await response.json(content_type=None)
                    raw_data = res.get("Data")
                    
                    if raw_data and len(raw_data) > self._index:
                        val = raw_data[self._index]
                        
                        if self._factor == "STATE":
                            self._state = {0:"Preparing", 1:"Preparing", 2:"Charging", 3:"Finishing", 4:"Faulted"}.get(val, f"Status {val}")
                        elif self._factor == "MODE":
                            self._state = {0:"STOP", 1:"FAST", 2:"ECO", 3:"GREEN"}.get(val, "Unknown")
                        else:
                            self._state = round(float(val) * self._factor, 2)
        except Exception as e:
            _LOGGER.debug("SolaX EVC (%s) update fail: %s", self._name_suffix, e)