# on-boarding-automation



----------------------------------------------------
Inside Ai-Agent folder

pip install -r requirements.txt

Add Keys in .env for below

GITHUB_TOKEN
OPENAI_API_KEY
LANGSMITH_API_KEY

----------------------------------------------------
Java Services:

Start all services in order: 

Config Server (localhost:8888)
Admin Server (localhost:9000)
Client App (localhost:8081)
Config Repo (https://github.com/pathaalok/config-repo)

----------------------------------------------------
Python Service:

uvicorn main:app --reload

API SPEC:



