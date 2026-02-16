"""
IoT API Endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.iot.mqtt_broker import mqtt_client, sensor_handler
from app.iot.sensor_integration import sensor_manager
from app.iot.digital_twin_core import digital_twin

router = APIRouter()


@router.get("/sensors")
async def get_sensors(
    sensor_type: str = None,
    project_id: str = None,
    current_user = Depends(get_current_user)
):
    """Get all sensors"""
    sensors = list(sensor_manager.sensors.values())
    
    if sensor_type:
        sensors = [s for s in sensors if s.sensor_type.value == sensor_type]
    
    if project_id:
        sensors = [s for s in sensors if s.project_id == project_id]
    
    return [{
        'id': s.id,
        'name': s.name,
        'type': s.sensor_type.value,
        'location': s.location,
        'is_active': s.is_active
    } for s in sensors]


@router.get("/sensors/{sensor_id}/data")
async def get_sensor_data(
    sensor_id: str,
    hours: int = 24,
    current_user = Depends(get_current_user)
):
    """Get sensor data"""
    data = sensor_manager.get_sensor_data(sensor_id, hours)
    return {'sensor_id': sensor_id, 'data': data}


@router.get("/sensors/summary")
async def get_sensor_summary(
    current_user = Depends(get_current_user)
):
    """Get sensor summary"""
    return sensor_manager.get_sensor_summary()


@router.get("/digital-twin/assets")
async def get_digital_twin_assets(
    level: str = None,
    current_user = Depends(get_current_user)
):
    """Get digital twin assets"""
    if level:
        assets = digital_twin.get_assets_in_space(level)
    else:
        assets = list(digital_twin.physical_assets.values())
    
    return [{
        'id': a.asset_id,
        'tag': a.asset_tag,
        'name': a.name,
        'type': a.asset_type,
        'location': a.location
    } for a in assets]


@router.get("/digital-twin/assets/{asset_id}")
async def get_asset_twin(
    asset_id: str,
    current_user = Depends(get_current_user)
):
    """Get asset digital twin data"""
    return digital_twin.get_asset_twin_data(asset_id)


@router.get("/digital-twin/overview")
async def get_digital_twin_overview(
    current_user = Depends(get_current_user)
):
    """Get digital twin overview"""
    return digital_twin.get_building_overview()


@router.post("/mqtt/publish")
async def mqtt_publish(
    topic: str,
    payload: dict,
    current_user = Depends(get_current_user)
):
    """Publish MQTT message"""
    import json
    await mqtt_client.publish(topic, json.dumps(payload).encode())
    return {'status': 'published'}
