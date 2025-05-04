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

API SPEC:

API:
http://127.0.0.1:8000/questionare

REQ: 
{
    "base_branch": "main",
    "new_branch": "new-onboarding",
    "questions": [
        "Partition",
        "Eligible SOR Codes (Example: ACCT/SOR,DEAL/SOR)",
        "BUS UNIT",
        "RCC RULES"
    ],
    "answers": {
        "0": "P2",
        "1": "Acct/sor1,DEAL/sor2",
        "2": "Test",
        "3": "COUNTRY,LOB,TYPE,DOC_CAT,DOC_TYPE,INV_REF,RCC CN,LOB1,ACCT,1,12,AlRCC US,LOB1,DEAL,1,,Al1RCCUS,,,,143,Al1RCC"
    }
}


