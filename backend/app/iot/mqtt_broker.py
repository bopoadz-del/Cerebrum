"""
MQTT Broker Integration
HiveMQ/AWS IoT Core MQTT client for sensor data
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

import aiomqtt
import paho.mqtt.client as mqtt

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MQTTMessage:
    """MQTT message"""
    topic: str
    payload: bytes
    qos: int
    retain: bool
    timestamp: datetime


@dataclass
class SensorReading:
    """Sensor reading from MQTT"""
    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    timestamp: datetime
    location: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MQTTClient:
    """Async MQTT client"""
    
    def __init__(
        self,
        broker_host: str = None,
        broker_port: int = 1883,
        username: str = None,
        password: str = None,
        use_tls: bool = False
    ):
        self.broker_host = broker_host or settings.MQTT_BROKER_HOST
        self.broker_port = broker_port or settings.MQTT_BROKER_PORT
        self.username = username or settings.MQTT_USERNAME
        self.password = password or settings.MQTT_PASSWORD
        self.use_tls = use_tls
        
        self.client: Optional[aiomqtt.Client] = None
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.connected = False
        self._task: Optional[asyncio.Task] = None
    
    async def connect(self):
        """Connect to MQTT broker"""
        try:
            tls_params = aiomqtt.TLSParameters() if self.use_tls else None
            
            self.client = aiomqtt.Client(
                hostname=self.broker_host,
                port=self.broker_port,
                username=self.username,
                password=self.password,
                tls_params=tls_params
            )
            
            await self.client.__aenter__()
            self.connected = True
            
            logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            
            # Start message loop
            self._task = asyncio.create_task(self._message_loop())
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MQTT broker"""
        self.connected = False
        
        if self._task:
            self._task.cancel()
        
        if self.client:
            await self.client.__aexit__(None, None, None)
        
        logger.info("Disconnected from MQTT broker")
    
    async def _message_loop(self):
        """Main message loop"""
        async with self.client.messages() as messages:
            async for message in messages:
                await self._handle_message(message)
    
    async def _handle_message(self, message: aiomqtt.Message):
        """Handle incoming MQTT message"""
        topic = message.topic.value
        
        mqtt_msg = MQTTMessage(
            topic=topic,
            payload=message.payload,
            qos=message.qos,
            retain=message.retain,
            timestamp=datetime.utcnow()
        )
        
        # Call subscribed handlers
        for pattern, handlers in self.subscriptions.items():
            if self._topic_matches(pattern, topic):
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            asyncio.create_task(handler(mqtt_msg))
                        else:
                            handler(mqtt_msg)
                    except Exception as e:
                        logger.error(f"Error in MQTT handler: {e}")
    
    def _topic_matches(self, pattern: str, topic: str) -> bool:
        """Check if topic matches pattern"""
        # Simple wildcard matching
        if pattern == topic:
            return True
        
        if pattern.endswith('/#'):
            prefix = pattern[:-2]
            return topic.startswith(prefix)
        
        if '#' in pattern or '+' in pattern:
            # More complex wildcard handling
            pattern_parts = pattern.split('/')
            topic_parts = topic.split('/')
            
            if len(pattern_parts) != len(topic_parts) and '#' not in pattern:
                return False
            
            for i, p in enumerate(pattern_parts):
                if p == '#':
                    return True
                if p == '+':
                    continue
                if i >= len(topic_parts) or p != topic_parts[i]:
                    return False
            
            return True
        
        return False
    
    async def subscribe(self, topic: str, handler: Callable):
        """Subscribe to topic"""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
            
            if self.connected and self.client:
                await self.client.subscribe(topic)
                logger.info(f"Subscribed to: {topic}")
        
        self.subscriptions[topic].append(handler)
    
    async def unsubscribe(self, topic: str, handler: Callable = None):
        """Unsubscribe from topic"""
        if topic in self.subscriptions:
            if handler:
                self.subscriptions[topic] = [
                    h for h in self.subscriptions[topic] if h != handler
                ]
            else:
                del self.subscriptions[topic]
            
            if not self.subscriptions.get(topic) and self.connected:
                await self.client.unsubscribe(topic)
                logger.info(f"Unsubscribed from: {topic}")
    
    async def publish(self, topic: str, payload: bytes, qos: int = 0, retain: bool = False):
        """Publish message to topic"""
        if not self.connected or not self.client:
            logger.warning("Cannot publish: not connected to MQTT broker")
            return
        
        await self.client.publish(topic, payload, qos=qos, retain=retain)


class SensorDataHandler:
    """Handle sensor data from MQTT"""
    
    def __init__(self, mqtt_client: MQTTClient):
        self.mqtt = mqtt_client
        self.readings: List[SensorReading] = []
        self.max_readings = 10000
        self.reading_handlers: List[Callable] = []
    
    async def initialize(self):
        """Initialize sensor data handler"""
        # Subscribe to sensor topics
        await self.mqtt.subscribe('sensors/+/data', self._handle_sensor_data)
        await self.mqtt.subscribe('sensors/+/status', self._handle_sensor_status)
    
    async def _handle_sensor_data(self, message: MQTTMessage):
        """Handle sensor data message"""
        try:
            data = json.loads(message.payload)
            
            # Extract sensor ID from topic
            topic_parts = message.topic.split('/')
            sensor_id = topic_parts[1] if len(topic_parts) > 1 else 'unknown'
            
            reading = SensorReading(
                sensor_id=sensor_id,
                sensor_type=data.get('type', 'unknown'),
                value=data.get('value', 0),
                unit=data.get('unit', ''),
                timestamp=datetime.utcnow(),
                location=data.get('location'),
                metadata=data.get('metadata', {})
            )
            
            self.readings.append(reading)
            
            # Trim old readings
            if len(self.readings) > self.max_readings:
                self.readings = self.readings[-self.max_readings:]
            
            # Notify handlers
            for handler in self.reading_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(reading))
                    else:
                        handler(reading)
                except Exception as e:
                    logger.error(f"Error in reading handler: {e}")
        
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in sensor data: {message.payload}")
        except Exception as e:
            logger.error(f"Error handling sensor data: {e}")
    
    async def _handle_sensor_status(self, message: MQTTMessage):
        """Handle sensor status message"""
        try:
            data = json.loads(message.payload)
            logger.info(f"Sensor status update: {data}")
        except Exception as e:
            logger.error(f"Error handling sensor status: {e}")
    
    def on_reading(self, handler: Callable):
        """Register reading handler"""
        self.reading_handlers.append(handler)
    
    def get_readings(
        self,
        sensor_id: str = None,
        sensor_type: str = None,
        limit: int = 100
    ) -> List[SensorReading]:
        """Get sensor readings"""
        readings = self.readings
        
        if sensor_id:
            readings = [r for r in readings if r.sensor_id == sensor_id]
        
        if sensor_type:
            readings = [r for r in readings if r.sensor_type == sensor_type]
        
        return sorted(readings, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def get_latest_reading(self, sensor_id: str) -> Optional[SensorReading]:
        """Get latest reading for a sensor"""
        readings = [r for r in self.readings if r.sensor_id == sensor_id]
        return max(readings, key=lambda x: x.timestamp) if readings else None


# Global MQTT client
mqtt_client = MQTTClient()
sensor_handler = SensorDataHandler(mqtt_client)
