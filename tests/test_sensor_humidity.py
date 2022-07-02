import logging
from lennoxs30api.s30api_async import (
    LENNOX_STATUS_NOT_EXIST,
    LENNOX_STATUS_GOOD,
    LENNOX_STATUS_NOT_AVAILABLE,
    lennox_system,
    lennox_zone,
)
from custom_components.lennoxs30 import (
    DS_RETRY_WAIT,
    Manager,
)
import pytest
from custom_components.lennoxs30.const import LENNOX_DOMAIN

from custom_components.lennoxs30.sensor import (
    S30HumiditySensor,
)

from homeassistant.const import TEMP_CELSIUS, PERCENTAGE, DEVICE_CLASS_HUMIDITY

from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
)


from unittest.mock import patch


@pytest.mark.asyncio
async def test_humidity_sensor(hass, manager: Manager, caplog):
    manager._is_metric = False
    system: lennox_system = manager._api._systemList[0]
    zone: lennox_zone = system.getZone(0)
    s = S30HumiditySensor(hass, manager, zone)

    assert s.unique_id == (system.unique_id() + "_" + str(zone.id) + "_H").replace(
        "-", ""
    )
    assert s.name == system.name + "_" + zone.name + "_humidity"
    assert s.available == True
    assert s.should_poll == False
    assert s.available == True
    assert s.update() == True
    assert len(s.extra_state_attributes) == 0

    assert s.state == zone.humidity
    assert s.unit_of_measurement == PERCENTAGE

    assert s.device_class == DEVICE_CLASS_HUMIDITY
    assert s.state_class == STATE_CLASS_MEASUREMENT

    identifiers = s.device_info["identifiers"]
    for x in identifiers:
        assert x[0] == LENNOX_DOMAIN
        assert x[1] == zone.unique_id


@pytest.mark.asyncio
async def test_humidity_sensor_subscription(hass, manager: Manager, caplog):
    system: lennox_system = manager._api._systemList[0]
    zone: lennox_zone = system.getZone(0)
    s = S30HumiditySensor(hass, manager, zone)
    await s.async_added_to_hass()

    with patch.object(s, "schedule_update_ha_state") as update_callback:
        manager._is_metric = False
        set = {"humidity": zone.humidity + 1}
        zone.attr_updater(set, "humidity")
        zone.executeOnUpdateCallbacks()
        assert update_callback.call_count == 1
        assert s.state == zone.humidity

    with patch.object(s, "schedule_update_ha_state") as update_callback:
        manager.updateState(DS_RETRY_WAIT)
        assert update_callback.call_count == 1
        assert s.available == False
