#!/usr/bin/env python3
"""
CTA Transit Tracker MQTT Client

This module fetches real-time arrival predictions from the Chicago Transit Authority (CTA)
API for buses and trains, and publishes the data to an MQTT broker.

Required environment variables:
- MQTT_BROKER: MQTT broker hostname (default: localhost)
- MQTT_USER: MQTT username (default: mqtt)
- MQTT_PASSWORD: MQTT password
- CTA_API_KEY_BUS: CTA Bus Tracker API key
- CTA_API_KEY_RAIL: CTA Train Tracker API key

Author: [Your Name]
Date: [Current Date]
"""

import os
import logging
import logging.handlers
from typing import List, Optional, Dict, Any
import datetime
import time
from dataclasses import dataclass
from abc import ABC, abstractmethod

import paho.mqtt.client as mqtt
import requests
from lxml import etree, objectify


# Configuration from environment variables
CONFIG = {
    'MQTT_BROKER': os.environ.get('MQTT_BROKER', 'localhost'),
    'MQTT_USER': os.environ.get('MQTT_USER', 'mqtt'),
    'MQTT_PASSWORD': os.environ.get('MQTT_PASSWORD', None),
    'CTA_API_KEY_BUS': os.environ.get('CTA_API_KEY_BUS', None),
    'CTA_API_KEY_RAIL': os.environ.get('CTA_API_KEY_RAIL', None),
    'UPDATE_INTERVAL': int(os.environ.get('UPDATE_INTERVAL',30))  # seconds
}

# API Endpoints
CTA_BUS_API_URL = 'http://www.ctabustracker.com/bustime/api/v2/getpredictions'
CTA_RAIL_API_URL = 'http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx'


@dataclass
class TransitStop:
    """Represents a transit stop configuration"""
    stop_id: str
    route: Optional[str] = None
    topic: Optional[str] = None
    
    def get_topic(self) -> str:
        """Generate MQTT topic for this stop"""
        if self.topic:
            return self.topic
        
        if self.route:
            return f"{self.stop_id}/{self.route}"
        return f"{self.stop_id}"


class Logger:
    """Centralized logging configuration"""
    @staticmethod
    def setup_logger(name: str = 'CTATransitTracker') -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Syslog handler (if available)
        try:
            syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
            syslog_handler.setLevel(logging.ERROR)
            logger.addHandler(syslog_handler)
        except Exception:
            pass  # Syslog not available (e.g., on Windows)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger


class MQTTManager:
    """Manages MQTT client connection and publishing"""
    
    def __init__(self, broker: str, username: str, password: Optional[str], logger: logging.Logger):
        self.broker = broker
        self.logger = logger
        self.client = mqtt.Client()
        
        if username and password:
            self.client.username_pw_set(username, password)
        
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.connected = False
        
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the client receives a CONNACK response from the server"""
        self.logger.info(f"Connected to MQTT broker at {datetime.datetime.now()}")
        
        if rc == 0:
            self.logger.info(f"Successfully connected to {self.broker} (code: {rc})")
            self.connected = True
        else:
            self.logger.error(f"Failed to connect to {self.broker} (code: {rc})")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the server"""
        self.logger.warning(f"Disconnected from MQTT broker at {datetime.datetime.now()}")
        self.connected = False
        
        if rc != 0:
            self.logger.error(f"Unexpected disconnection (code: {rc}). Attempting to reconnect...")
            self._reconnect()
    
    def _reconnect(self):
        """Attempt to reconnect to the MQTT broker"""
        try:
            self.logger.info("Attempting to reconnect to MQTT broker...")
            self.client.connect(self.broker)
        except Exception as e:
            self.logger.error(f"Failed to reconnect: {e}")
    
    def connect(self):
        """Establish connection to MQTT broker"""
        try:
            self.client.connect(self.broker)
            self.client.loop_start()  # Start the network loop in a separate thread
            time.sleep(1)  # Give it time to connect
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def publish(self, topic: str, message: Any):
        """Publish a message to a topic"""
        if not self.connected:
            self.logger.warning(f"Not connected to broker. Cannot publish to {topic}")
            return False
        
        try:
            result = self.client.publish(topic, str(message))
            if result.rc == 0:
                self.logger.debug(f"Published {message} to {topic}")
                return True
            else:
                self.logger.error(f"Failed to publish to {topic}: {result.rc}")
                return False
        except Exception as e:
            self.logger.error(f"Error publishing to {topic}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()


class CTAApiClient(ABC):
    """Abstract base class for CTA API clients"""
    
    def __init__(self, api_key: str, logger: logging.Logger):
        self.api_key = api_key
        self.logger = logger
    
    @abstractmethod
    def get_predictions(self, stop_id: str, route: Optional[str] = None) -> Any:
        """Get predictions for a stop"""
        pass
    
    @abstractmethod
    def calculate_etas(self, predictions: Any) -> List[int]:
        """Calculate ETAs from predictions"""
        pass


class CTABusClient(CTAApiClient):
    """Client for CTA Bus Tracker API"""
    
    def get_predictions(self, stop_id: str, route: Optional[str] = None) -> Any:
        """Fetch bus predictions from CTA API"""
        params = {
            'key': self.api_key,
            'stpid': stop_id
        }
        if route:
            params['rt'] = route
        
        try:
            response = requests.get(CTA_BUS_API_URL, params=params, timeout=10)
            response.raise_for_status()
            return objectify.fromstring(response.text)
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch bus predictions for stop {stop_id}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing bus predictions: {e}")
            return None
    
    def calculate_etas(self, predictions: Any) -> List[int]:
        """Calculate ETAs in seconds from bus predictions"""
        eta_list = []
        
        if predictions is None or not hasattr(predictions, 'prd'):
            return [-1]  # No predictions available
        
        current_time = datetime.datetime.now()
        
        for prediction in predictions.prd:
            try:
                # Parse predicted arrival time
                predicted_arrival = datetime.datetime.strptime(
                    prediction.prdtm.text, '%Y%m%d %H:%M'
                )
                
                # Calculate ETA in seconds
                eta = predicted_arrival - current_time
                eta_seconds = max(0, eta.seconds)  # Ensure non-negative
                eta_list.append(eta_seconds)
                
            except Exception as e:
                self.logger.warning(f"Error parsing bus prediction: {e}")
                continue
        
        return eta_list if eta_list else [-1]


class CTARailClient(CTAApiClient):
    """Client for CTA Train Tracker API"""
    
    def get_predictions(self, stop_id: str, route: Optional[str] = None) -> Any:
        """Fetch rail predictions from CTA API"""
        params = {
            'key': self.api_key,
            'stpid': stop_id
        }
        
        try:
            response = requests.get(CTA_RAIL_API_URL, params=params, timeout=10)
            response.raise_for_status()
            return objectify.fromstring(response.text.encode('utf-8'))
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch rail predictions for stop {stop_id}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing rail predictions: {e}")
            return None
    
    def calculate_etas(self, predictions: Any) -> List[int]:
        """Calculate ETAs in seconds from rail predictions"""
        eta_list = []
        
        if predictions is None or not hasattr(predictions, 'eta'):
            return [-1]  # No predictions available
        
        current_time = datetime.datetime.now()
        
        for prediction in predictions.eta:
            try:
                # Parse predicted arrival time
                predicted_arrival = datetime.datetime.strptime(
                    prediction.arrT.text, '%Y%m%d %H:%M:%S'
                )
                
                # Calculate ETA in seconds
                eta = predicted_arrival - current_time
                eta_seconds = max(0, eta.seconds)  # Ensure non-negative
                eta_list.append(eta_seconds)
                
            except Exception as e:
                self.logger.warning(f"Error parsing rail prediction: {e}")
                continue
        
        return eta_list if eta_list else [-1]


class CTATransitTracker:
    """Main application class for CTA Transit Tracker"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = Logger.setup_logger()
        
        # Validate configuration
        self._validate_config()
        
        # Initialize components
        self.mqtt_manager = MQTTManager(
            broker=config['MQTT_BROKER'],
            username=config['MQTT_USER'],
            password=config['MQTT_PASSWORD'],
            logger=self.logger
        )
        
        self.bus_client = CTABusClient(
            api_key=config['CTA_API_KEY_BUS'],
            logger=self.logger
        )
        
        self.rail_client = CTARailClient(
            api_key=config['CTA_API_KEY_RAIL'],
            logger=self.logger
        )
        
        # Configure stops to monitor
        self.bus_stops = self._configure_bus_stops()
        self.rail_stops = self._configure_rail_stops()
    
    def _validate_config(self):
        """Validate required configuration"""
        if not self.config.get('CTA_API_KEY_BUS'):
            raise ValueError("CTA_API_KEY_BUS environment variable is required")
        
        if not self.config.get('CTA_API_KEY_RAIL'):
            raise ValueError("CTA_API_KEY_RAIL environment variable is required")
        
        if not self.config.get('MQTT_PASSWORD'):
            self.logger.warning("MQTT_PASSWORD not set - using anonymous connection")
    
    def _configure_bus_stops(self) -> List[TransitStop]:
        """Configure bus stops to monitor"""
        # Add your bus stops here
        return [
            # Sheridan East (Northbound)
            TransitStop(stop_id='1151', route='77'),
            TransitStop(stop_id='1151', route='151'),
            
            # Sheridan West (Southbound)
            TransitStop(stop_id='1074', route='151'),
            
            # Sheridan Loop Buses
            TransitStop(stop_id='1074', route='134'),
            TransitStop(stop_id='1074', route='143'),
            TransitStop(stop_id='1074', route='156'),
        ]
    
    def _configure_rail_stops(self) -> List[TransitStop]:
        """Configure rail stops to monitor"""
        return [
            # Wellington Northbound
            TransitStop(stop_id='30231'),
            
            # Wellington Southbound
            TransitStop(stop_id='30232'),
        ]
    
    def update_predictions(self):
        """Update all transit predictions and publish to MQTT"""
        self.logger.info("Updating transit predictions...")
        
        # Update bus predictions
        for stop in self.bus_stops:
            try:
                predictions = self.bus_client.get_predictions(stop.stop_id, stop.route)
                etas = self.bus_client.calculate_etas(predictions)
                
                if etas:
                    topic = f"CTApredictions/BUS/{stop.get_topic()}"
                    self.mqtt_manager.publish(topic, etas[0])
                    
            except Exception as e:
                self.logger.error(f"Error updating bus stop {stop.stop_id}: {e}")
        
        # Calculate downtown express bus (minimum of loop buses)
        self._update_downtown_express()
        
        # Update rail predictions
        for stop in self.rail_stops:
            try:
                predictions = self.rail_client.get_predictions(stop.stop_id)
                etas = self.rail_client.calculate_etas(predictions)
                
                if etas:
                    topic = f"CTApredictions/RAIL/{stop.get_topic()}"
                    self.mqtt_manager.publish(topic, etas[0])
                    
            except Exception as e:
                self.logger.error(f"Error updating rail stop {stop.stop_id}: {e}")
    
    def _update_downtown_express(self):
        """Calculate and publish the next downtown express bus"""
        downtown_routes = ['134', '143', '156']
        downtown_etas = []
        
        for route in downtown_routes:
            try:
                predictions = self.bus_client.get_predictions('1074', route)
                etas = self.bus_client.calculate_etas(predictions)
                if etas and etas[0] != -1:
                    downtown_etas.append(etas[0])
            except Exception as e:
                self.logger.error(f"Error getting downtown bus {route}: {e}")
        
        if downtown_etas:
            min_eta = min(downtown_etas)
            self.mqtt_manager.publish("CTApredictions/BUS/dwtnEXP", min_eta)
    
    def run(self):
        """Main application loop"""
        self.logger.info("Starting CTA Transit Tracker...")
        self.logger.info(f"Current time: {datetime.datetime.now()}")
        
        # Connect to MQTT broker
        if not self.mqtt_manager.connect():
            self.logger.error("Failed to connect to MQTT broker. Exiting.")
            return
        
        # Main update loop
        while True:
            try:
                self.update_predictions()
                self.logger.debug(f"Updated predictions at {datetime.datetime.now()}")
                
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal. Shutting down...")
                break
                
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
            
            # Wait before next update
            time.sleep(self.config['UPDATE_INTERVAL'])
        
        # Cleanup
        self.mqtt_manager.disconnect()
        self.logger.info("CTA Transit Tracker stopped.")


def main():
    """Entry point for the application"""
    try:
        tracker = CTATransitTracker(CONFIG)
        tracker.run()
    except Exception as e:
        logging.error(f"Failed to start CTA Transit Tracker: {e}")
        raise


if __name__ == "__main__":
    main()