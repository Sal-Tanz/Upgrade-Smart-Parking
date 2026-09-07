"""
MQTT Service untuk komunikasi dengan perangkat IoT (ESP32).

Mengimplementasi:
- Publishing buzzer commands ke ESP32
- Subscribing slot status updates dari ESP32
- Subscribing vehicle entry events dari ESP32
"""
import json
import logging
from datetime import datetime, timezone
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from api.config import settings

logger = logging.getLogger(__name__)


class MQTTService:
    """
    MQTT Service class untuk mengelola komunikasi dengan broker MQTT.

    Topics:
    - parking/buzzer/alert: Publish commands ke ESP32
    - parking/slot/status: Subscribe updates dari ESP32
    - parking/vehicle/entry: Subscribe vehicle entry dari ESP32
    """

    def __init__(self):
        """Initialize MQTT client dengan konfigurasi dari settings."""
        self.broker = settings.MQTT_BROKER
        self.port = settings.MQTT_PORT

        # Create MQTT client with CallbackAPIVersion.VERSION2
        # See: https://github.com/eclipse-paho/paho.mqtt.python
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"smart_parking_api_{datetime.now().timestamp()}",
            protocol=mqtt.MQTTv5
        )

        # Setup callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish

        # Connection state
        self.connected = False
        self._unacked_messages = set()  # Track QoS 1/2 messages

        # Callbacks for subscribed topics
        self._on_slot_status_callback: Optional[Callable] = None
        self._on_vehicle_entry_callback: Optional[Callable] = None

        logger.info(f"MQTT Service initialized for {self.broker}:{self.port}")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback ketika terhubung ke MQTT broker."""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker at {self.broker}:{self.port}")

            # Subscribe to topics
            topics = [
                (settings.MQTT_TOPIC_SLOT, 1),
                (settings.MQTT_TOPIC_ENTRY, 1)
            ]
            client.subscribe(topics)
            logger.info(f"Subscribed to topics: {topics}")
        else:
            self.connected = False
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")

    def _on_disconnect(self, client, userdata, *args, **kwargs):
        """Callback ketika terputus dari MQTT broker."""
        self.connected = False
        rc = args[1] if len(args) > 1 else (args[0] if args else 0)
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker. Return code/reason: {rc}")
        else:
            logger.info("Disconnected from MQTT broker")


    def _on_message(self, client, userdata, msg):
        """Callback ketika menerima pesan dari subscribed topic."""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode('utf-8'))

            logger.debug(f"Received message on topic {topic}: {payload}")

            # Route to appropriate callback
            if topic == settings.MQTT_TOPIC_SLOT and self._on_slot_status_callback:
                self._on_slot_status_callback(payload)
            elif topic == settings.MQTT_TOPIC_ENTRY and self._on_vehicle_entry_callback:
                self._on_vehicle_entry_callback(payload)
            else:
                logger.warning(f"No callback registered for topic: {topic}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse MQTT message payload: {e}")
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")

    def _on_publish(self, client, userdata, mid, reason_code, properties):
        """Callback when message is successfully published (QoS 1/2)."""
        logger.debug(f"Message {mid} published successfully")
        # Remove from unacked messages if tracking is needed
        self._unacked_messages.discard(mid)

    async def connect(self):
        """Connect ke MQTT broker dan start loop."""
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            logger.info("MQTT client loop started")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

    async def disconnect(self):
        """Disconnect dari MQTT broker dan stop loop."""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT client disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting from MQTT broker: {e}")

    async def publish_buzzer(self, buzzer_pattern: str, plate_text: str, reason: str):
        """
        Publish buzzer command ke ESP32.

        Args:
            buzzer_pattern: Pattern buzzer (SUCCESS_TONE, SHORT_1X, MEDIUM_2X, LONG_3X, SHORT_DOUBLE)
            plate_text: Nomor plat kendaraan
            reason: Alasan perintah buzzer
        """
        if not self.connected:
            logger.warning("MQTT not connected. Cannot publish buzzer command.")
            return False

        try:
            payload = {
                "action": "ALERT",
                "buzzer_pattern": buzzer_pattern,
                "plate": plate_text,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            result = self.client.publish(
                topic=settings.MQTT_TOPIC_BUZZER,
                payload=json.dumps(payload),
                qos=1
            )

            # Track message for QoS 1/2 acknowledgment
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self._unacked_messages.add(result.mid)
                logger.info(f"Published buzzer command: {buzzer_pattern} for plate {plate_text} (mid={result.mid})")
                return True
            else:
                logger.error(f"Failed to publish buzzer command. RC: {result.rc}")
                return False

        except Exception as e:
            logger.error(f"Error publishing buzzer command: {e}")
            return False

    def on_slot_status(self, callback: Callable):
        """
        Register callback untuk slot status updates.

        Args:
            callback: Function yang dipanggil ketika ada slot status update
                     Signature: callback(payload: dict)
        """
        self._on_slot_status_callback = callback
        logger.info("Registered slot status callback")

    def on_vehicle_entry(self, callback: Callable):
        """
        Register callback untuk vehicle entry events.

        Args:
            callback: Function yang dipanggil ketika ada vehicle entry event
                     Signature: callback(payload: dict)
        """
        self._on_vehicle_entry_callback = callback
        logger.info("Registered vehicle entry callback")

    def is_connected(self) -> bool:
        """Check apakah MQTT client terhubung ke broker."""
        return self.connected


# Singleton instance
mqtt_service = MQTTService()
