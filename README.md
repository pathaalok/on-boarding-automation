# on-boarding-automation

This Repo is POC for automation of on boarding

---------------------------------------------------
Design :

![on_boarding_automation drawio](https://github.com/user-attachments/assets/2d66f967-c4c8-448f-a747-f6fe33a1839f)

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

----------------------------------------------------
Angular UI:

Inside on-boarding-ui in cmd run:

For dependency : npm install

To start application : ng serve


![image](https://github.com/user-attachments/assets/de09e8b5-11dd-4722-8bcb-1d51c1bb8935)


