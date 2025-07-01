import os
import time
from pyngrok import ngrok
from dotenv import load_dotenv
from pathlib import Path
import subprocess

# Load environment variables from .env
load_dotenv(dotenv_path=Path(__file__).parent / '.env')
NGROK_AUTH_TOKEN = os.getenv('NGROK_AUTH_TOKEN')

# Set ngrok auth token
if NGROK_AUTH_TOKEN:
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)
else:
    print('NGROK_AUTH_TOKEN not found in .env file!')

# Kill all previous ngrok tunnels
ngrok.kill()

# Start Streamlit app in the background
streamlit_cmd = [
    'streamlit', 'run', 'main_app.py', '--server.headless', 'true', '--server.port', '8501'
]
streamlit_proc = subprocess.Popen(streamlit_cmd)

# Wait for Streamlit to start
time.sleep(5)

# Start ngrok tunnel
public_url = ngrok.connect(8501)
print(f"Public app URL: {public_url}")

try:
    # Keep the script running while Streamlit is running
    streamlit_proc.wait()
finally:
    ngrok.kill() 