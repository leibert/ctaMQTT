# CTA Transit Tracker MQTT Client

A Python application that fetches real-time arrival predictions from the Chicago Transit Authority (CTA) API and publishes them to an MQTT broker. Perfect for home automation, transit displays, or any project that needs CTA arrival data.

I care about a few routes near where I live in Lakeview Chicago. For rail you can get the stop IDs from CTA's documentation (https://www.transitchicago.com/developers/ttdocs/). For bus stop IDs, you can usually find the stop ID on the physical sign or you can find it on Google Maps, by clicking the Bus Stop, and the ID will be towards the top.

Some of the stops have multiple bus routes going downtown, where I generally want to take the first one that arrives. 
update_predictions._update_downtown_express() gets the predictions of the relevant interlined routes and publishes the ETA of the next arriving bus to 'CTApredictions/BUS/dtwnEXP'

Code commenting and most of this readme AI generated, errors are likely present.


## Features

- 🚌 **Bus Tracker Integration** - Real-time bus arrival predictions
- 🚊 **Train Tracker Integration** - Real-time train arrival predictions
- 📡 **MQTT Publishing** - Publishes arrival times to MQTT topics for easy integration


## Prerequisites

- Python 3.6 or higher
- CTA API Keys (both Bus and Train)
- MQTT Broker (e.g., Mosquitto, HiveMQ, CloudMQTT)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/cta-mqtt-tracker.git
cd cta-mqtt-tracker
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export MQTT_BROKER="your-mqtt-broker.com"
export MQTT_USER="your-mqtt-username"
export MQTT_PASSWORD="your-mqtt-password"
export CTA_API_KEY_BUS="your-cta-bus-api-key"
export CTA_API_KEY_RAIL="your-cta-train-api-key"
```

## Getting CTA API Keys

1. **Bus Tracker API Key**:
   - Visit [CTA Bus Tracker API](https://www.transitchicago.com/developers/bustracker/)
   - Register for a developer account
   - Request a Bus Tracker API key

2. **Train Tracker API Key**:
   - Visit [CTA Train Tracker API](https://www.transitchicago.com/developers/traintracker/)
   - Use the same developer account
   - Request a Train Tracker API key

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MQTT_BROKER` | MQTT broker hostname/IP | `localhost` | No |
| `MQTT_USER` | MQTT username | `mqtt` | No |
| `MQTT_PASSWORD` | MQTT password | None | Yes* |
| `CTA_API_KEY_BUS` | CTA Bus Tracker API key | None | Yes |
| `CTA_API_KEY_RAIL` | CTA Train Tracker API key | None | Yes |

*Required if your MQTT broker uses authentication

### Adding Transit Stops

To monitor different stops, edit the configuration methods in `CTAmqtt.py`:

#### Bus Stops
```python
def _configure_bus_stops(self) -> List[TransitStop]:
    return [
        TransitStop(stop_id='1151', route='77'),   # Stop 1151, Route 77
        TransitStop(stop_id='1074', route='151'),  # Stop 1074, Route 151
        # Add your stops here
    ]
```

#### Train Stops
```python
def _configure_rail_stops(self) -> List[TransitStop]:
    return [
        TransitStop(stop_id='30231'),  # Wellington Northbound
        TransitStop(stop_id='30232'),  # Wellington Southbound
        # Add your stops here
    ]
```

### Finding Stop IDs

- **Bus Stops**: Use the [CTA Bus Tracker](https://www.transitchicago.com/bustracker/) to find stop IDs
- **Train Stops**: Use the [CTA Train Tracker](https://www.transitchicago.com/traintracker/) to find platform IDs

## Usage

### Basic Usage

Run the application:
```bash
python3 CTAmqtt.py
```

### Running as a Service

For continuous operation, consider running as a systemd service:

1. Create a service file `/etc/systemd/system/cta-mqtt.service`:
```ini
[Unit]
Description=CTA Transit Tracker MQTT Client
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/cta-mqtt-tracker
Environment="MQTT_BROKER=your-broker.com"
Environment="MQTT_USER=your-username"
Environment="MQTT_PASSWORD=your-password"
Environment="CTA_API_KEY_BUS=your-bus-key"
Environment="CTA_API_KEY_RAIL=your-rail-key"
ExecStart=/usr/bin/python3 /path/to/cta-mqtt-tracker/CTAmqtt.py
Restart=always

[Install]
WantedBy=multi-user.target
```

2. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cta-mqtt.service
sudo systemctl start cta-mqtt.service
```

### Docker Support

Build and run with Docker:
```bash
docker build -t cta-mqtt-tracker .
docker run -d \
  -e MQTT_BROKER=your-broker.com \
  -e MQTT_USER=your-username \
  -e MQTT_PASSWORD=your-password \
  -e CTA_API_KEY_BUS=your-bus-key \
  -e CTA_API_KEY_RAIL=your-rail-key \
  --name cta-tracker \
  cta-mqtt-tracker
```

## MQTT Topics

The application publishes to the following topic patterns:

### Bus Predictions
- Format: `CTApredictions/BUS/{stop_id}/{route}`
- Example: `CTApredictions/BUS/1151/77`
- Special: `CTApredictions/BUS/dwtnEXP` (next downtown express bus)

### Train Predictions
- Format: `CTApredictions/RAIL/{platform_id}`
- Example: `CTApredictions/RAIL/30231`

### Published Data

Each topic receives the ETA in seconds for the next arrival. A value of `-1` indicates no predictions available.

## Integration Examples

### Home Assistant

Add to your `configuration.yaml`:
```yaml
sensor:
  - platform: mqtt
    name: "Bus 77 Northbound"
    state_topic: "CTApredictions/BUS/1151/77"
    unit_of_measurement: "seconds"
    value_template: "{{ value | int }}"
    
  - platform: mqtt
    name: "Red Line Northbound"
    state_topic: "CTApredictions/RAIL/30231"
    unit_of_measurement: "seconds"
    value_template: "{{ value | int }}"
```

### Node-RED

Subscribe to topics using MQTT In nodes and create flows to:
- Display on dashboards
- Send notifications when buses are approaching
- Control smart home devices based on transit timing

### Python Client Example

```python
import paho.mqtt.client as mqtt

def on_message(client, userdata, message):
    eta_seconds = int(message.payload.decode())
    eta_minutes = eta_seconds // 60
    print(f"Next arrival in {eta_minutes} minutes")

client = mqtt.Client()
client.on_message = on_message
client.connect("your-broker.com", 1883)
client.subscribe("CTApredictions/BUS/1151/77")
client.loop_forever()
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   CTA Bus API   │     │  CTA Rail API   │     │   MQTT Broker   │
└────────┬────────┘     └────────┬────────┘     └────────▲────────┘
         │                       │                         │
         │ HTTP                  │ HTTP                    │ MQTT
         │                       │                         │
         ▼                       ▼                         │
┌────────────────────────────────────────────────────────┴────────┐
│                      CTA Transit Tracker                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Bus Client  │  │ Rail Client │  │MQTT Manager │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└──────────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Common Issues

1. **"Failed to connect to MQTT broker"**
   - Check your MQTT_BROKER environment variable
   - Verify network connectivity
   - Ensure MQTT broker is running

2. **"No predictions available" (-1 values)**
   - Verify your API keys are correct
   - Check if the stop/route combination is valid
   - Some routes may not run at certain times

3. **"Error parsing predictions"**
   - The CTA API may be temporarily unavailable
   - Check your internet connection
   - Verify API keys haven't expired

### Debug Mode

Enable debug logging by modifying the logger level:
```python
logger.setLevel(logging.DEBUG)
```


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Chicago Transit Authority for providing the APIs
- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) for MQTT client
- [lxml](https://lxml.de/) for XML parsing

