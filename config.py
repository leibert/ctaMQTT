import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration settings for CTA MQTT Application
    
    All settings can be overridden using environment variables.
    Copy .env.example to .env and update with your values.
    """
    MQTT_BROKER = os.getenv("MQTT_BROKER", "192.168.1.101")
    MQTT_USER = os.getenv("MQTT_USER", "mqtt")
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "VZh%&u2eQc9VN@9S")
    API_KEY_BUS = os.getenv('CTA_API_KEY_BUS', 'gMizvTqmWYsGazSAEq4vrmE4Z')
    API_KEY_RAIL = os.getenv('CTA_API_KEY_RAIL', '325bdc7c566d4c36807003e5c740ca7c')
    BUS_API_URL = 'http://www.ctabustracker.com/bustime/api/v2'
    RAIL_API_URL = 'http://lapi.transitchicago.com/api/1.0'

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration settings"""
        required_vars = [
            ('MQTT_BROKER', cls.MQTT_BROKER),
            ('MQTT_USER', cls.MQTT_USER),
            ('MQTT_PASSWORD', cls.MQTT_PASSWORD),
            ('CTA_API_KEY_BUS', cls.API_KEY_BUS),
            ('CTA_API_KEY_RAIL', cls.API_KEY_RAIL)
        ]
        
        missing = [var[0] for var in required_vars if not var[1]]
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Please check your .env file"
            )
        return True
