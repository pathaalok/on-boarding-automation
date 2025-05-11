from dotenv import load_dotenv
import os
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from submit_on_boarding_service import run_langgraph, QAState,event_stream
from fastapi.responses import StreamingResponse
import google.generativeai as genai
import uuid
from submit_on_boarding_service import fetch_content,build_user_prompt,call_ai_model

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


rule_file = os.getenv("RULES_YML") 

# Set up Gemini API
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# =================== On Board Questionare =====================


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

    
        # 2. **SOR Codes**: Must follow this format: ACCT/SOR,DEAL/SOR (one or more items, comma-separated).

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
    
    convo = session["convo"]

    # User confirmed their answers
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

    # Handle edit mode
    if user_msg.edit_index is not None:
        index = user_msg.edit_index
        question = full_prompts[index]

        # Tell Gemini what is being edited
        convo.send_message(f"Revisiting this question:\n{question}\nUser answered: {user_msg.message}")
        bot_response = convo.last.text

        # Check if invalid
        if "invalid" in bot_response.lower() or "please re-enter" in bot_response.lower():
            return {
                "response": bot_response,
                "question": full_prompts[index]
            }

        # Save new answer and update history
        session["answers"][index] = {"user": user_msg.message, "bot": bot_response}
        session["history"][index].append(user_msg.message)

        return {
            "response": bot_response,
            "preview": session["answers"],
            "history": session["history"]
        }

    # Normal (non-edit) flow
    index = session["index"]

    convo.send_message(user_msg.message)
    bot_response = convo.last.text

    # If answer is invalid
    if "invalid" in bot_response.lower() or "please re-enter" in bot_response.lower():
        return {
            "response": bot_response,
            "question": full_prompts[index]
        }

    # Save valid answer
    if 0 <= index < len(full_prompts):
        session["answers"][index] = {"user": user_msg.message, "bot": bot_response}
        session["history"][index].append(user_msg.message)

    # Move to next question
    session["index"] += 1

    # If all questions answered, show preview
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

    # Otherwise, continue to next question
    return {
        "response": full_prompts[session["index"]]
    }


# =================== Verify Questionare =====================

class VerifyQAInput(BaseModel):
    questions: List[str]
    answers: Dict[int, str]

verify_qa_store = {
    "test":{"questions":["Enter Partition?","Enter Sampling Data"],"answers":{"0":"p1","1":"123"}},
    "test2":{"questions":["Enter Partition?","Enter Eligible SOR Codes ? (Example: ACCT/SOR,DEAL/SOR)","Enter BUS UNIT","Enter RCC RULES","Enter Sampling Rule Ref","Enter Sampling Id","Enter Sampling Data"],"answers":{"0":"P2","1":"ACCT/123","2":"Test","3":"COUNTRY,LOB,TYPE,DOC_CAT,DOC_TYPE,INV_REF,RCC\nCN,LOB1,ACCT,1,12,AlRCC\nUS,LOB1,DEAL,1,,Al1RCC\nUS,,,,123,RCC4","4":"123","5":"123","6":"123"}}
}

@app.post("/store_verify_qa")
def store_qa(data: VerifyQAInput):
    session_id = str(uuid.uuid4())
    verify_qa_store[session_id] = data
    return {"session_id": session_id, "message": "QA data stored successfully"}

@app.get("/all_verify_qa")
def get_verify_all_qa():
    return verify_qa_store

@app.get("/verify-qa/{session_id}/{branch_name}")
def verify_qa(session_id: str,branch_name:str):
    questionare = verify_qa_store.get(session_id)
    data: QAState = {
        "questions": questionare.get("questions"),
        "answers": questionare.get("answers"),
        "branch": branch_name
    }
    print(data)
    print("=================")
    rules = fetch_content(branch_name,rule_file)
    system_prompt = f"""
        You are an expert onboarding verifyinh assistant. You are provided with a RCC rules configurations.

        Partions Info:
            P0 is Federated
            P1 to P4 are non Regulated
            P5 is Regulated

        Rule Types Description :
            non_regulated_rccRule (when Partition is non Regulated and #COUNTRY|LOB|TYPE|DOC_CAT|DOC_TYPE have data from "RCC RULES" INPUT DATA),
            inv_ref_id_rccRule (when Partition is Regulated and #COUNTRY|INV_REF have data from "RCC RULES" INPUT DATA),
            non_regulated_inv_ref_id_rccRule  (when Partition is non Regulated and #COUNTRY|INV_REF have data from "RCC RULES" from INPUT DATA)
 
        
        You must:
        - Consider the data only from "RCC RULES" from INPUT DATA
        - Check whether a given key input for that section is already present. Only report conflicts where an input rule attempts to redefine an existing rule with a different RCC value.
        - Collect all conflict rules and line numbers from "RCC RULES" from INPUT DATA and give respose in below format

        rule => rule data from RCC Rules input data
        lineNumber => rule line number from RCC Rules input data
        
        [
            {{
                'rule':'',
                'lineNumber':'',
                'existingRcc': '',
                'inputRcc': ''
            }}
        ]
         
        \n\n{rules}
    """
    user_prompt = build_user_prompt(data)
    result = call_ai_model(system_prompt, user_prompt,"json")
    return result



@app.delete("/verify_qa/{session_id}")
def get_verify_all_qa(session_id: str):
    del verify_qa_store[session_id]
    return verify_qa_store

# =================== Submit Questionare =====================


class QAInput(BaseModel):
    questions: List[str]
    answers: Dict[int, str]
    base_branch: Optional[str] = None
    new_branch: Optional[str] = None
    jira_no: Optional[str] = None

submit_qa_store = {
    
}

@app.post("/store_submit_qa")
def store_qa(data: QAInput):
    session_id = str(uuid.uuid4())
    submit_qa_store[session_id] = data
    return {"session_id": session_id, "message": "QA data stored successfully"}

@app.get("/all_submit_qa")
def get_submit_all_qa():
    return submit_qa_store


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
