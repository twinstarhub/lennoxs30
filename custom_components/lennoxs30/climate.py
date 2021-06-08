import logging
import asyncio
from . import s30api_async

from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    CURRENT_HVAC_COOL, CURRENT_HVAC_HEAT, CURRENT_HVAC_IDLE, HVAC_MODE_DRY,
    HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL, ATTR_HVAC_MODE,
    HVAC_MODE_HEAT_COOL, PRESET_AWAY, SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE, SUPPORT_PRESET_MODE, SUPPORT_FAN_MODE,
    FAN_ON, FAN_AUTO, ATTR_TARGET_TEMP_LOW, ATTR_TARGET_TEMP_HIGH,
    PRESET_NONE,
)

from homeassistant.components.climate.const import (
    CURRENT_HVAC_COOL, CURRENT_HVAC_HEAT, CURRENT_HVAC_IDLE,
    HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL,
    HVAC_MODE_HEAT_COOL, PRESET_AWAY, SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE, SUPPORT_PRESET_MODE, SUPPORT_FAN_MODE,
    FAN_ON, FAN_AUTO, ATTR_TARGET_TEMP_LOW, ATTR_TARGET_TEMP_HIGH,
    PRESET_NONE,
)
from homeassistant.const import (TEMP_CELSIUS, TEMP_FAHRENHEIT,
    ATTR_TEMPERATURE)

_LOGGER = logging.getLogger(__name__)
#_LOGGER.setLevel(logging.DEBUG)

# HA doesn't have a 'circulate' state defined for fan.
FAN_CIRCULATE = 'circulate'

PRESET_CANCEL_HOLD = 'Cancel Hold'
PRESET_SCHEDULE_OVERRIDE = 'Schedule Hold'

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE |
                 SUPPORT_TARGET_TEMPERATURE_RANGE |
                 SUPPORT_PRESET_MODE |
                 SUPPORT_FAN_MODE)

FAN_MODES = [
    FAN_AUTO, FAN_ON, FAN_CIRCULATE
]

HVAC_MODES = [
    HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_HEAT_COOL
]

HVAC_ACTIONS = [
    CURRENT_HVAC_IDLE, CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL
]

TEMP_UNITS = [
    TEMP_FAHRENHEIT, TEMP_CELSIUS
]

DOMAIN = "lennoxs30"


from homeassistant.const import (CONF_EMAIL, CONF_PASSWORD)


async def async_setup_platform(hass, config, add_entities, discovery_info: s30api_async.s30api_async=None ):
    # Discovery info is the API that we passed in.
    _LOGGER.debug("climate:async_setup_platform enter")
    if discovery_info is None:
        _LOGGER.error("climate:async_setup_platform expecting API in discovery_info, found None")
        return False
    theType = str(type(discovery_info))
    if 's30api_async' not in theType:
        _LOGGER.error("climate:async_setup_platform expecting API in discovery_info, found [" + str(theType) + "]")
        return False

    climate_list = []

    s30api = discovery_info
    for system in s30api.getSystems():
        for zone in system.getZones():
            if zone.getTemperature() != None:
                _LOGGER.info("Create S30 Climate system [" + system.sysId + "] zone [" + zone.name + "]")
                climate = S30Climate(hass, s30api, system, zone)
                climate_list.append(climate)
            else:
                _LOGGER.info("Skipping S30 Climate system [" + system.sysId + "] zone [" + zone.name + "]")

    add_entities(climate_list, True)
    _LOGGER.debug("climate:async_setup_platform exit")
    return True

class S30Climate(ClimateEntity):
    """Class for Lennox iComfort WiFi thermostat."""

    def __init__(self, hass, s30api: s30api_async, system: s30api_async.lennox_system, zone: s30api_async.lennox_zone):
        """Initialize the climate device."""
        self.hass = hass
        self._s30api = s30api
        self._system = system
        self._system.registerOnUpdateCallback(self.update_callback)
        self._zone = zone
        self._min_temp = 60
        self._max_temp = 80
        self._myname = self._system.name + '_' + self._zone.name
        s = 'climate' + "." +  self._system.sysId + '-' + str(self._zone.id)
        s = s.replace("-","")

    @property
    def unique_id(self) -> str:
        return (self._system.sysId + '_' + str(self._zone.id)).replace("-","")

    def update_callback(self):
        _LOGGER.info("update_callback myname [" + self._myname + "]")
        self.async_schedule_update_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {         
        }        

    def update(self):
        """Update data from the thermostat API."""
        return True

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        return self._myname

    @property
    def supported_features(self):
        _LOGGER.debug("climate:supported_features name[" + self._myname + "] support_flags [" + str(SUPPORT_FLAGS) + "]")
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_FAHRENHEIT

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        minTemp = None
        if self._zone.heatingOption == True:
            minTemp = self._zone.minHsp
        if self._zone.coolingOption == True:
            if minTemp == None:
                minTemp = self._zone.minCsp
            else:
                minTemp = min(minTemp, self._zone.minCsp)
        if minTemp != None:
            return minTemp
        return super().min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""

        maxTemp = None
        if self._zone.heatingOption == True:
            maxTemp = self._zone.maxHsp
        if self._zone.coolingOption == True:
            if maxTemp == None:
                maxTemp = self._zone.maxCsp
            else:
                maxTemp = max(maxTemp, self._zone.maxCsp)
        if maxTemp != None:
            return maxTemp
        return super().max_temp

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._zone.getTargetTemperatureF()

    @property
    def current_temperature(self):
        """Return the current temperature."""
        t = self._zone.getTemperature()
        _LOGGER.debug("climate:current_temperature name[" + self._myname + "] temperature [" + str(t) + "]")
        return t

    @property
    def target_temperature_high(self):
        """Return the highbound target temperature we try to reach."""
        # TODO Need to figure out heatcool mode and the string, for now we will return csp
        _LOGGER.debug("climate:target_temperature_high name[" + self._myname + "] temperature [" + str(self._zone.csp) + "]")
        return self._zone.csp

    @property
    def target_temperature_low(self):
        """Return the lowbound target temperature we try to reach."""
        # TODO Need to figure out heatcool mode and the string, for now we will return csp
        _LOGGER.debug("climate:target_temperature_low name[" + self._myname + "] temperature [" + str(self._zone.hsp) + "]")
        return self._zone.hsp

    @property
    def current_humidity(self):
        """Return the current humidity."""
        h = self._zone.getHumidity() 
        _LOGGER.debug("climate:current_temperature name[" + self._myname + "] humidity [" + str(h) + "]")
        return h
 
    @property
    def hvac_mode(self):
        """Return the current hvac operation mode."""
        r = self._zone.getSystemMode()
        _LOGGER.debug("climate:hvac_mode name[" + self._myname + "] mode [" + r + "]")
        return r

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes."""
        modes = []
        modes.append(HVAC_MODE_OFF)
        if self._zone.coolingOption == True:
            modes.append(HVAC_MODE_COOL)
        if self._zone.heatingOption == True:
            modes.append(HVAC_MODE_HEAT)
        if self._zone.dehumidificationOption == True:
            modes.append(HVAC_MODE_DRY)
        return modes

    @property
    def hvac_action(self):
        """Return the current hvac state/action."""
        # TODO may need to translate
        return self._zone.tempOperation

    @property
    def preset_mode(self):
        if self._zone.overrideActive == True:
            return PRESET_SCHEDULE_OVERRIDE
        scheduleId = self._zone.scheduleId
        if scheduleId is None:
            return None
        schedule = self._system.getSchedule(scheduleId)
        if schedule is None:
            return None
        return schedule.name

    @property
    def preset_modes(self):
        presets = []
        for schedule in self._system.getSchedules():
            # Everything above 16 seems to be internal schedules
            if schedule.id >= 16:
                continue
            presets.append(schedule.name)
        presets.append(PRESET_CANCEL_HOLD)
        _LOGGER.debug("climate:preset_modes name[" + self._myname + "] presets[" + str(presets) + "]")
        return presets

    async def async_set_preset_mode(self, preset_mode):
        _LOGGER.info("climate:async_set_preset_mode name[" + self._myname + "] preset_mode [" + preset_mode + "]")

        if preset_mode == PRESET_CANCEL_HOLD:
            return await self._zone.setScheduleHold(False)
        await self._zone.setSchedule(preset_mode)
        
#        if preset_mode == PRESET_AWAY:
#            self._turn_away_mode_on()
#        else:
#            self._turn_away_mode_off()


    @property
    def is_away_mode_on(self):
        """Return the current away mode status."""
        return False
#       return self._api.away_mode

    @property
    def fan_mode(self):
        """Return the current fan mode."""
        return self._zone.getFanMode()

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return FAN_MODES

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature"""

        r_hvacMode = None
        if kwargs.get(ATTR_HVAC_MODE) is not None:
            r_hvacMode = kwargs.get(ATTR_HVAC_MODE) 
        r_temperature = None
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            r_temperature = kwargs.get(ATTR_TEMPERATURE) 
        r_csp = None
        if kwargs.get(ATTR_TARGET_TEMP_HIGH) is not None:
            r_csp = kwargs.get(ATTR_TARGET_TEMP_HIGH) 
        r_hsp = None
        if kwargs.get(ATTR_TARGET_TEMP_LOW) is not None:
            r_hsp = kwargs.get(ATTR_TARGET_TEMP_LOW)

        _LOGGER.info("climate:async_set_temperature zone [" + self._myname + "] hvacMode [" + str(r_hvacMode) + "] temperature [" + str(r_temperature) + "] temp_high [" + str(r_csp) + "] temp_low [" + str(r_hsp) + "]")

        # A temperature must be specified
        if r_temperature is None and r_csp is None and r_hsp is None:
            _LOGGER.error("climate:async_set_temperature - no temperature given zone [" + self._myname + "] hvacMode [" + str(r_hvacMode) + "] temperature [" + str(r_temperature) + "] temp_high [" + str(r_csp) + "] temp_low [" + str(r_hsp) + "]")
            return

        # Either provide temperature or high/low but not both
        if r_temperature != None and (r_csp != None or r_hsp != None):
            _LOGGER.error("climate:async_set_temperature - pass either temperature or temp_high / low - zone [" + self._myname + "] hvacMode [" + str(r_hvacMode) + "] temperature [" + str(r_temperature) + "] temp_high [" + str(r_csp) + "] temp_low [" + str(r_hsp) + "]")
            return

        # If no temperature, must specify both high and low 
        if r_temperature == None and (r_csp == None or r_hsp == None):
            _LOGGER.error("climate:async_set_temperature - must provide both temp_high / low - zone [" + self._myname + "] hvacMode [" + str(r_hvacMode) + "] temperature [" + str(r_temperature) + "] temp_high [" + str(r_csp) + "] temp_low [" + str(r_hsp) + "]")
            return

        # If an HVAC mode is requested; and we are not in that mode, then the first step
        # is to switch the zone into that mode before setting the temperature
        if (r_hvacMode != None and r_hvacMode != self.hvac_mode):
            _LOGGER.info("climate:async_set_temperature zone [" + self._myname + "] setting hvacMode [" + str(r_hvacMode) + "]")
            result = await self.async_set_hvac_mode(r_hvacMode)
            if result == False:
                _LOGGER.error("climate:async_set_temperature zone [" + self._myname + "] failed setting hvacMode [" + str(r_hvacMode) + "]")
                return

        if (r_hvacMode == None):
            r_hvacMode = self.hvac_mode

        if r_temperature is not None:
            if self.hvac_mode == HVAC_MODE_COOL:
                _LOGGER.info("climate:async_set_temperature set_temperature system in cool mode - zone [" + self._myname + "] temperature [" + str(r_temperature) + "]")
                result = await self._zone.setCoolSPF(r_temperature)
                if result == False:
                    _LOGGER.error("climate:async_set_temperature - failed - zone [" + self._myname + "] temperature [" + str(r_temperature) + "]")
                    return False
                return True
            elif self.hvac_mode == HVAC_MODE_HEAT:
                _LOGGER.info("climate:async_set_temperature set_temperature system in heat mode - zone [" + self._myname + "] sp [" + str(r_temperature) + "]")
                result = await self._zone.setCoolSPF(r_temperature)
                if result == False:
                    _LOGGER.error("climate:async_set_temperature - failed - zone [" + self._myname + "] temperature [" + str(r_temperature) + "]")
                    return False
                return True
            else:
                _LOGGER.error("set_temperature System Mode is [" + r_hvacMode + "] unable to set temperature")
                return False
        else:
            _LOGGER.info("climate:async_set_temperature zone [" + self._myname + "] csp [" + str(r_csp) + "] hsp [" + str(r_hsp) + "]")
            result = await self._zone.setHeatCoolSPF(r_hsp, r_csp)

    async def async_set_fan_mode(self, fan_mode):
        """Set new fan mode."""
        _LOGGER.info("climate:async_set_temperature name[" + self._myname + "] fanMode [ " + str(fan_mode) + "]")
        await self._zone.setFanMode(fan_mode)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new hvac operation mode."""
        _LOGGER.info("climate:async_set_hvac_mode name[" + self._myname + "] fanMode [ " + str(hvac_mode) + "]")
        await self._zone.setHVACMode(hvac_mode)
        # We'll do a couple polls until we get the state
        for x in range(1, 10):
            await asyncio.sleep(0.5)
            await self._s30api.retrieve()
            if self._zone.getSystemMode() == hvac_mode:
                _LOGGER.info("async_set_hvac_mode - got change with fast poll iteration [" + str(x) + "]")
                return
        _LOGGER.info("async_set_hvac_mode - unabled to retrieve change with fast poll")


    def _turn_away_mode_on(self):
        raise NotImplementedError
#        """Turn away mode on."""
#        self._api.away_mode = 1

    def _turn_away_mode_off(self):
        raise NotImplementedError
#        """Turn away mode off."""
#        self._api.away_mode = 0