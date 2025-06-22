# CTA MQTT Service

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install python-dotenv paho-mqtt requests lxml
   ```
3. Create your environment file:
   ```bash
   cp .env.example .env
   ```
4. Edit `.env` and add your credentials:
   - Get your CTA Bus API key from: [Bus API Documentation](http://www.transitchicago.com/assets/1/6/cta_Bus_Tracker_API_Developer_Guide_and_Documentation_20160929.pdf)
   - Get your CTA Rail API key from: [Train API Documentation](https://www.transitchicago.com/developers/traintracker/)

5. Run the service:
   ```bash
   python CTAmqtt.py
   ```

## Security Notes

- Never commit the `.env` file to version control
- Keep your API keys secure and rotate them periodically
- Use environment-specific `.env` files for different deployments
