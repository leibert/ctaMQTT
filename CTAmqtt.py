import logging
import logging.handlers
import paho.mqtt.client as mqtt
import requests
import time
import datetime
from lxml import objectify
from config import Config

class CTATransitAPI:
    """Base class for CTA API interactions"""
    def get_predictions(self, stop_id):
        raise NotImplementedError
    
    def get_etas(self, predictions):
        raise NotImplementedError

class CTABusAPI(CTATransitAPI):
    """Handles CTA Bus API interactions"""
    def get_predictions(self, stop_id, route=None):
        params = {'key': Config.API_KEY_BUS, 'stpid': stop_id, 'rt': route}
        response = requests.get(f'{Config.BUS_API_URL}/getpredictions', params=params)
        return objectify.fromstring(response.text)

    def get_etas(self, predictions, current_time):
        eta_list = []
        if not hasattr(predictions, 'prd'):
            return [-1]
        
        for prediction in predictions.prd:
            predicted_arrival = datetime.datetime.strptime(prediction.prdtm.text, '%Y%m%d %H:%M')
            eta = predicted_arrival - current_time
            eta_list.append(eta.seconds)
        return eta_list

class CTARailAPI(CTATransitAPI):
    """Handles CTA Rail API interactions"""
    def get_predictions(self, platform_id):
        params = {'key': Config.API_KEY_RAIL, 'stpid': platform_id}
        response = requests.get(f'{Config.RAIL_API_URL}/ttarrivals.aspx', params=params)
        return objectify.fromstring(response.text.encode('utf-8'))

    def get_etas(self, predictions, current_time):
        eta_list = []
        if not hasattr(predictions, 'eta'):
            return [-1]
        
        for prediction in predictions.eta:
            predicted_arrival = datetime.datetime.strptime(prediction.arrT.text, '%Y%m%d %H:%M:%S')
            eta = predicted_arrival - current_time
            eta_list.append(eta.seconds)
        return eta_list

class CTAMQTTClient:
    """Handles MQTT connection and message publishing"""
    def __init__(self):
        self.client = mqtt.Client()
        self.client.username_pw_set(Config.MQTT_USER, password=Config.MQTT_PASSWORD)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.bus_api = CTABusAPI()
        self.rail_api = CTARailAPI()
        
        # Setup logging
        self.logger = logging.getLogger('CTALogger')
        self.logger.setLevel(logging.ERROR)
        handler = logging.handlers.SysLogHandler(address='/dev/log')
        self.logger.addHandler(handler)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("Successfully connected to MQTT broker")
        else:
            self.logger.error(f"Failed to connect to MQTT broker with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self.logger.warning("Unexpected MQTT disconnection. Attempting reconnect...")
            try:
                self.client.connect(Config.MQTT_BROKER)
            except Exception as e:
                self.logger.error(f"Reconnection failed: {str(e)}")

    def start(self):
        """Start the MQTT client and prediction updates"""
        try:
            self.client.connect(Config.MQTT_BROKER)
            self.client.loop_start()
            
            while True:
                try:
                    self._update_predictions()
                except Exception as e:
                    self.logger.error(f"Error updating predictions: {str(e)}")
                time.sleep(30)
                
        except Exception as e:
            self.logger.error(f"Fatal error: {str(e)}")
            raise

    def _update_predictions(self):
        """Update all bus and train predictions"""
        current_time = datetime.datetime.now()
        
        # 2970 NLSD Bus predictions
        self._publish_bus_prediction('1151', '77', current_time)
        self._publish_bus_prediction('1151', '151', current_time)
        self._publish_bus_prediction('1074', '151', current_time)
        
        # Express bus predictions
        express_routes = ['134', '143', '156']
        dtwn_times = []
        for route in express_routes:
            eta = self._get_bus_eta('1074', route, current_time)
            dtwn_times.append(eta)
            self.client.publish(f"CTApredictions/BUS/1074/{route}", eta)
        
        self.client.publish("CTApredictions/BUS/dwtnEXP", min(dtwn_times))
        
        # Train predictions
        self._publish_rail_prediction('30231', current_time)  # Wellington Northbound
        self._publish_rail_prediction('30232', current_time)  # Wellington Southbound

    def _publish_bus_prediction(self, stop_id, route, current_time):
        eta = self._get_bus_eta(stop_id, route, current_time)
        self.client.publish(f"CTApredictions/BUS/{stop_id}/{route}", eta)

    def _get_bus_eta(self, stop_id, route, current_time):
        predictions = self.bus_api.get_predictions(stop_id, route)
        etas = self.bus_api.get_etas(predictions, current_time)
        return etas[0]

    def _publish_rail_prediction(self, platform_id, current_time):
        predictions = self.rail_api.get_predictions(platform_id)
        etas = self.rail_api.get_etas(predictions, current_time)
        self.client.publish(f"CTApredictions/RAIL/{platform_id}", etas[0])

if __name__ == "__main__":
    client = CTAMQTTClient()
    client.start()
