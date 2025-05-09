from dotenv import load_dotenv
import os
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from submit_on_boarding_service import run_langgraph, QAState,event_stream
from fastapi.responses import StreamingResponse
import google.generativeai as genai

# Load environment variables
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =================== On Board Questionare =====================


# Set up Gemini API
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# In-memory state
sessions = {}

# Define list of questions
questions = [
    "Enter Partition?",
    "Enter Eligible SOR Codes ? (Example: ACCT/SOR,DEAL/SOR)",
    "Enter BUS UNIT",
    "Enter RCC RULES",
    "Enter Sampling Rule Ref",
    'Enter Sampling Id',
    'Enter Sampling Data'
]

full_prompts = [
    "Enter Partition ( P0, P1, P2, P3, P4, P5)",
    "Enter Eligible SOR Codes (Example Format: ACCT/SOR,DEAL/SOR)",
    "Enter BUS UNIT ",
    "Enter RCC RULES ",
    "Enter Sampling Rule Ref ",
    'Enter Sampling Id ',
    'Enter Sampling Data '
]

class UserMessage(BaseModel):
    session_id: str
    message: str
    edit_index: int = None

@app.post("/start")
def start_conversation():
    convo = model.start_chat(history=[])
    session_id = str(id(convo))

    questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(full_prompts)])

    prompt = f"""
        You are a validation assistant. Ask the following questions **one-by-one**. 
        Wait for the user's response before continuing. 

        ### Validation Rules:
        1. **Partition**: Only accept one of P0, P1, P2, P3, P4, P5. Reject and re-ask if invalid.
        2. **SOR Codes**: Must follow this format: ACCT/SOR,DEAL/SOR (one or more items, comma-separated).
        3. For other questions, you may use basic judgment to detect obviously incorrect inputs.

        ### Behavior:
        - If an answer is invalid, **explain the error** and **re-ask the same question**.
        - Once all answers are collected, return a preview with all Q&A and ask the user to confirm.

        ### Questions:
        {questions_text}
        """


    convo.send_message(prompt)
    sessions[session_id] = {
        "convo": convo,
        "answers": [None] * len(full_prompts),
        "index": 0,
        "confirmed": False,
        "history": [[] for _ in full_prompts]
    }
    return {"session_id": session_id, "question": convo.last.text}

@app.post("/message")
def process_message(user_msg: UserMessage):
    session = sessions.get(user_msg.session_id)
    if not session:
        return {"error": "Invalid session"}
    
    if "confirm" in user_msg.message.lower():
        formatted_answers = {str(i): ans["user"] for i, ans in enumerate(session["answers"])}
        final_output = {
            "questions": questions,
            "answers": formatted_answers
        }
        del sessions[user_msg.session_id]  # clear session after confirmation
        return {
            "response": "Thank you! Your responses have been confirmed and sent for review.",
            "final_output": final_output
        }

    convo = session["convo"]
    index = session["index"] if user_msg.edit_index is None else user_msg.edit_index

    # Send user message to Gemini
    convo.send_message(user_msg.message)
    bot_response = convo.last.text

    # Check if LLM thinks the answer is invalid
    if "invalid" in bot_response.lower() or "please re-enter" in bot_response.lower():
        return {
            "response": bot_response,
            "question": full_prompts[index]
        }

    # Save valid answer
    if 0 <= index < len(full_prompts):
        session["answers"][index] = {"user": user_msg.message, "bot": bot_response}
        session["history"][index].append(user_msg.message)

    if user_msg.edit_index is not None:
        return {
            "response": bot_response,
            "preview": session["answers"],
            "history": session["history"]
        }

    session["index"] += 1

    if session["index"] >= len(full_prompts):
        formatted_answers = {str(i): ans["user"] for i, ans in enumerate(session["answers"])}
        return {
            "response": "Here are your answers. Please review and confirm:",
            "preview": session["answers"],
            "history": session["history"],
            "json_output": {
                "questions": questions,
                "answers": formatted_answers
            }
        }

    return {
        "response": full_prompts[session["index"]]
    }



# =================== Submit Questionare =====================


class QAInput(BaseModel):
    questions: List[str]
    answers: Dict[int, str]
    base_branch: str
    new_branch: str
    jira_no: str


@app.get("/events")
async def sse_endpoint():
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

@app.post("/questionare")
def submit_qa(data: QAInput):
    state: QAState = {
        "questions": data.questions,
        "index": 0,
        "answers": data.answers,
        "command": "",
        "base_branch":data.base_branch,
        "branch_name": data.new_branch,
        "jira_no": data.jira_no,
        "sor_codes_content": "",
        "updated_sor_codes": "",
        "rules_content":"",
        "updated_rules": "",
        "bu_on_boarding_content": "",
        "updated_bu_on_boarding": "",
        "abort": False
    }

    result = run_langgraph(state)
    return {"status": "completed", "final_state": result}
