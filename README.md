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
![on_boarding_automation drawio](https://github.com/user-attachments/assets/2d66f967-c4c8-448f-a747-f6fe33a1839f)

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

Initial Screen:
![image](https://github.com/user-attachments/assets/77845eb9-962c-4f45-861b-f46fa4a1f3fd)


On submission events will be displayed in real time:
![image](https://github.com/user-attachments/assets/0d0c5068-a4b3-4f10-ab12-2457fa33ca4e)


DEMOS:
-

Design Video:
-


https://github.com/user-attachments/assets/6f8fd97e-207c-470f-990a-c2330c81309f




Application Video:
-



https://github.com/user-attachments/assets/704e5d08-a79a-4a04-ad8f-e4fd9e33eedc



