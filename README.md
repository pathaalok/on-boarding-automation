# On-Boarding-Automation

This Repo is POC for automation of on boarding

Technologies Used
-----------------

Python + Lang Graph

Spring Config Server

Spring boot Admin

Spring boot Client App

Angular UI

---------------------------------------------------
Design :
-
![UI_FLOW drawio](https://github.com/user-attachments/assets/c0d77b42-5b6f-41f1-8464-de5d6c556052)


----------------------------------------------------

Set Up:
-

Inside Ai-Agent folder

pip install -r requirements.txt

Add Keys in .env for below

GITHUB_TOKEN
OPENAI_API_KEY
LANGSMITH_API_KEY

Python Service:

uvicorn main:app --reload

----------------------------------------------------
Java Services:

Start all services in order: 

Config Server (localhost:8888)

Admin Server (localhost:9000)

Client App (localhost:8081)

Config Repo (https://github.com/pathaalok/config-repo)

----------------------------------------------------
Angular UI:

Inside on-boarding-ui in cmd run:

For dependency : npm install

To start application : ng serve

URL: http://localhost:4200/

Side Nav: 
![image](https://github.com/user-attachments/assets/ff4692bb-4cf5-4d28-85e9-487562073e5a)

On Boarding Manual:
![image](https://github.com/user-attachments/assets/5a06b67d-cd43-4da0-b431-9fa6be94347e)

On Boarding Chatbot:
![image](https://github.com/user-attachments/assets/dec09afd-72f7-49fd-a964-e211d840832e)

On Boarding Verify screen:
![image](https://github.com/user-attachments/assets/a20cb1a7-17ad-4671-a768-ddf018879043)


Submit Screen:

![image](https://github.com/user-attachments/assets/a2e177d0-a25e-448c-b8a1-d854e96de796)


On submission events will be displayed in real time:
![image](https://github.com/user-attachments/assets/0d0c5068-a4b3-4f10-ab12-2457fa33ca4e)

Sample PR created by Agent : https://github.com/pathaalok/config-repo/pull/56/files

DEMOS:
-

Design & Application Video:
-


https://github.com/user-attachments/assets/266e8512-c9e0-4fb0-b608-5bb3fb3b5270





