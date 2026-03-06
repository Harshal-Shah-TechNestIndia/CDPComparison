# CDPComparison
Compare CDP Reports [POC]

# Run Project in Docker
docker compose build --no-cache
docker compose up

# Run without Docker

- Create Venv and Activate it
python3 -m venv cdp
source cdp/bin/activate
pip3 install -r requirements.txt

Create .env file or add this to model client in agents.py
OPENAI_API_KEY = ""

Go to dir containing server.py
Run python3 server.py