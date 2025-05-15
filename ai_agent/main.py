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
    "Enter On Boarding Name",
    "Enter Partition ? (P0, P1, P2, P3, P4, P5)",
    "Enter Eligible SOR Codes ? (Example: ACCT/SOR,DEAL/SOR)",
    "Enter BUS UNIT",
    "Enter RCC RULES",
    "Enter Sampling Rule Ref",
    'Enter Sampling Id',
    'Enter Sampling Data'
]

class UserMessage(BaseModel):
    session_id: str
    message: str
    edit_index: int = None

@app.post("/start")
def start_conversation():
    convo = model.start_chat(history=[])
    session_id = str(id(convo))

    questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])

    prompt = f"""
        You are a validation assistant. Ask the following questions **one-by-one**. 
        Wait for the user's response before continuing. 

        ### Validation Rules:
        - **Partition**: Only accept one of P0, P1, P2, P3, P4, P5. Reject and re-ask if invalid.
        - **SOR Codes**: Must follow this format: ACCT/SOR,DEAL/SOR (one or more items, comma-separated).

        ### Behavior:
        - If an answer is invalid, **explain the error** and **re-ask the same question**.
        - Once all answers are collected, return a preview with all Q&A and ask the user to confirm.

        ### Questions:
        {questions_text}
        """


    convo.send_message(prompt)
    sessions[session_id] = {
        "convo": convo,
        "answers": [None] * len(questions),
        "index": 0,
        "confirmed": False,
        "history": [[] for _ in questions]
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
        question = questions[index]

        # Tell Gemini what is being edited
        convo.send_message(f"Revisiting this question:\n{question}\nUser answered: {user_msg.message}")
        bot_response = convo.last.text

        # Check if invalid
        if "invalid" in bot_response.lower() or "please re-enter" in bot_response.lower():
            return {
                "response": bot_response,
                "question": questions[index]
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
            "question": questions[index]
        }

    # Save valid answer
    if 0 <= index < len(questions):
        session["answers"][index] = {"user": user_msg.message, "bot": bot_response}
        session["history"][index].append(user_msg.message)

    # Move to next question
    session["index"] += 1

    # If all questions answered, show preview
    if session["index"] >= len(questions):
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
        "response": questions[session["index"]]
    }


# =================== Verify Questionare =====================

class VerifyQAInput(BaseModel):
    questions: List[str]
    answers: Dict[int, str]

verify_qa_store = {
}

@app.post("/store_verify_qa")
def store_qa(data: VerifyQAInput):
    session_id = str(uuid.uuid4())
    verify_qa_store[session_id] = data
    return {"session_id": session_id, "message": "QA data stored successfully"}


@app.put("/store_verify_qa/{session_id}")
def store_qa(session_id: str,data: VerifyQAInput):
    verify_qa_store[session_id] = data
    return {"session_id": session_id, "message": "QA data stored successfully"}

@app.get("/all_verify_qa")
def get_verify_all_qa():
    return verify_qa_store

@app.get("/verify-qa/{session_id}/{branch_name}")
def verify_qa(session_id: str,branch_name:str):
    print(verify_qa_store)
    questionare = verify_qa_store.get(str(session_id))
    data: QAState = {
        "questions": questionare.questions,
        "answers": questionare.answers,
        "branch": branch_name
    }
    print(data)
    print("=================")
    rules = fetch_content(branch_name,rule_file)
    system_prompt = f"""
        You are an expert onboarding verification assistant.  Your task is to identify RCC rule conflicts based on provided data.  Follow these steps precisely:

**Data:**

        Partions Info:
            P0 is Federated
            P1 to P4 are non Regulated
            P5 is Regulated

        Rule Types Description :
            non_regulated_rccRule (when Partition is non Regulated and COUNTRY|LOB|TYPE|DOC_CAT|DOC_TYPE have data from "RCC RULES" INPUT DATA),
            inv_ref_id_rccRule (when Partition is Regulated and COUNTRY|INV_REF have data from "RCC RULES" INPUT DATA),
            non_regulated_inv_ref_id_rccRule  (when Partition is non Regulated and COUNTRY|INV_REF have data from "RCC RULES" from INPUT DATA)
 
        
       

**Conflict Detection Algorithm:**

1. **Partition Determination:** Determine the partition type (Federated, Regulated, Non-Regulated) from the INPUT DATA's.

2. **Rule Type Selection:** For each line in the "RCC RULES" input data (Q5), determine the appropriate rule type based on the populated fields and the partition type:
    * `non_regulated_rccRule`:  Partition is Non-Regulated AND COUNTRY|LOB|TYPE|DOC_CAT|DOC_TYPE are populated.
    * `inv_ref_id_rccRule`: Partition is Regulated AND COUNTRY|INV_REF are populated.
    * `non_regulated_inv_ref_id_rccRule`: Partition is Non-Regulated AND COUNTRY|INV_REF are populated.

3. **Key Generation:**  For each line, construct the key string based on the selected rule type's required fields.  Use square brackets `[]` and pipe symbols `|` as delimiters.  For example: `[US|LOB1|ACCT|11|11]` or `[US|123]`.

4. **Conflict Detection:** Compare each generated key against the keys in the corresponding rule type within the "Existing Rules".  A conflict exists ONLY if:
    * The key is should be exactly same (dont assume alike or similar) in both the "Existing Rules" and the "RCC RULES" input data and the RCC values are different.
    * Double check while considering it as conflict.

5. **Output:**  Report conflicts in the specified JSON format, including the original rule line, line number, existing RCC value, input RCC value and Reason for conflict.  If no conflicts are found, return an empty JSON array: `[]`.

**Perform conflict detection using the provided data and algorithm.  Show your work by explicitly stating the rule type, key, and conflict determination for each line in the RCC RULES input data.**
        
        [
            {{
                "rule": "original CSV line from RCC RULES",
                "lineNumber": "line number in RCC RULES input",
                "existingRcc": "value in existing config",
                "inputRcc": "value in input",
                "reasonForConflict":"Provide reason for conflict"
            }}
        ]

        \n\n 
        Existing Rules:
        \n\n{rules}

        \n\n
    """
    user_prompt = build_user_prompt(data)
    result = call_ai_model(system_prompt, user_prompt,"json")
    return result



@app.delete("/verify_qa/{session_id}")
def delete_verify_qa(session_id: str):
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
        "abort": False,
        "test_case_report": ""
    }

    result = run_langgraph(state)
    return {"status": "completed", "final_state": result}


@app.delete("/submit_qa/{session_id}")
def delete_submit_qa(session_id: str):
    del submit_qa_store[session_id]
    return submit_qa_store