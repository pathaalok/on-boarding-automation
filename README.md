# on-boarding-automation

Java Services:

Start all services in order:

Config Server (localhost:8888)

Admin Server (localhost:9000)

Client App (localhost:8081)

Config Repo (https://github.com/pathaalok/config-repo)

Ai-Agent:

pip install -r requirements.txt

Add values for below in .env

GITHUB_TOKEN
OPENAI_API_KEY
LANGSMITH_API_KEY


```
langgraph dev
```

You should see the following output:
```
- 🚀 API: http://127.0.0.1:2024
- 🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- 📚 API Docs: http://127.0.0.1:2024/docs
```
