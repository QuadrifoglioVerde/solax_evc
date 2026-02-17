import logging
import async_timeout
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import (
    UnitOfEnergy, UnitOfPower, UnitOfElectricCurrent, 
    UnitOfElectricPotential, UnitOfTemperature, UnitOfTime
)

_LOGGER = logging.getLogger(__name__)

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
    ("CHG Single", 13, UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, 0.1),
    ("CHG Total", 15, UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, 0.1),
    ("Temperature Plug", 23, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, 1),
    ("Temperature PCB", 24, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, 1),
]

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    host = config.get("host")
    pwd = config.get("password")
    session = async_get_clientsession(hass)

    async def async_get_data():
        url = f"http://{host}"
        payload = f"optType=ReadRealTimeData&pwd={pwd}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            async with async_timeout.timeout(10):
                async with session.post(url, data=payload, headers=headers) as response:
                    data = await response.json(content_type=None)
                    if "Data" not in data:
                        raise UpdateFailed("V odpovědi chybí pole 'Data'")
                    return data["Data"]
        except Exception as err:
            raise UpdateFailed(f"Chyba při komunikaci s nabíječkou: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="solax_evc_sensor",
        update_method=async_get_data,
        update_interval=timedelta(seconds=60),
    )

    # První načtení dat
    await coordinator.async_refresh()

    async_add_entities(
        [SolaxEVCSensor(coordinator, info, host) for info in SENSOR_TYPES]
    )

class SolaxEVCSensor(SensorEntity):
    def __init__(self, coordinator, info, host):
        self.coordinator = coordinator
        self._name_suffix, self._index, self._unit, self._device_class, self._factor = info
        
        self._attr_name = f"SolaX EVC {self._name_suffix}"
        clean_name = self._name_suffix.lower().replace(" ", "_")
        self._attr_unique_id = f"solax_evc_{host}_{clean_name}"
        self._attr_native_unit_of_measurement = self._unit
        self._attr_device_class = self._device_class
        
        if self._device_class == SensorDeviceClass.ENERGY:
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def should_poll(self):
        return False

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def native_value(self):
        raw_data = self.coordinator.data
        if not raw_data or len(raw_data) <= self._index:
            return None
        
        val = raw_data[self._index]
        if self._factor == "STATE":
            return {0:"Preparing", 1:"Preparing", 2:"Charging", 3:"Finishing", 4:"Faulted"}.get(val, f"Status {val}")
        if self._factor == "MODE":
            return {0:"STOP", 1:"FAST", 2:"ECO", 3:"GREEN"}.get(val, "Unknown")
        
        return round(float(val) * self._factor, 2)

    async def async_added_to_hass(self):
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
