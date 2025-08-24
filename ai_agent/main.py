from dotenv import load_dotenv
import os
from fastapi import FastAPI,HTTPException, UploadFile, File
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from submit_on_boarding_service import run_langgraph, QAState,event_stream
from fastapi.responses import StreamingResponse
import aiohttp
import asyncio
import base64
import json
import google.generativeai as genai
import uuid
from submit_on_boarding_service import fetch_content,build_user_prompt,call_ai_model
from supervisor_agent import run_workflow_step1_sync, run_workflow_step2, store_workflow_state, get_workflow_state, delete_workflow_state

# Load environment variables
load_dotenv()

# API Configuration
class APIConfig:
    def __init__(self):
        self.base_url = os.getenv("TARGET_API_BASE_URL", "https://api.example.com")
        self.username = os.getenv("API_USERNAME", "default_user")
        self.password = os.getenv("API_PASSWORD", "default_password")
        self.endpoint = os.getenv("API_ENDPOINT", "/process-file")
    
    def get_auth_header(self):
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"

api_config = APIConfig()

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

    
# =================== File Upload =====================

def call_external_api(file_content: bytes, filename: str) -> Dict:
    """
    Call external API with basic auth for a single file
    """
    try:
        import requests
        
        # Prepare the request data
        files = {'file': (filename, file_content)}
        headers = {
            'Authorization': api_config.get_auth_header()
        }
        
        url = f"{api_config.base_url}{api_config.endpoint}"
        
        # Make the API call with basic auth
        response = requests.post(url, files=files, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            return {
                "filename": filename,
                "status": "success",
                "api_response": result
            }
        else:
            return {
                "filename": filename,
                "status": "error",
                "error": f"API returned status {response.status_code}: {response.text}"
            }
                    
    except Exception as e:
        return {
            "filename": filename,
            "status": "error",
            "error": f"Exception occurred: {str(e)}"
        }

@app.post("/upload-files")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Accept multiple files uploaded from UI, call external API for each file in parallel,
    and consolidate results
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Read all files first
    file_data = []
    for file in files:
        try:
            content = await file.read()
            file_data.append({
                "content": content,
                "filename": file.filename,
                "content_type": file.content_type,
                "size": len(content)
            })
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading file {file.filename}: {str(e)}")
    
    # Call external API for each file
    api_results = []
    for file_info in file_data:
        try:
            result = call_external_api(file_info["content"], file_info["filename"])
            api_results.append(result)
        except Exception as e:
            api_results.append({
                "filename": file_info["filename"],
                "status": "error",
                "error": f"Task failed with exception: {str(e)}"
            })
    
    # Process results and handle exceptions
    processed_results = []
    for i, result in enumerate(api_results):
        if isinstance(result, Exception):
            processed_results.append({
                "filename": file_data[i]["filename"],
                "status": "error",
                "error": f"Task failed with exception: {str(result)}"
            })
        else:
            processed_results.append(result)
    
    # Consolidate results
    successful_files = [r for r in processed_results if r["status"] == "success"]
    failed_files = [r for r in processed_results if r["status"] == "error"]
    
    consolidated_result = {
        "message": f"Processed {len(files)} files",
        "summary": {
            "total_files": len(files),
            "successful": len(successful_files),
            "failed": len(failed_files)
        },
        "results": processed_results,
        "successful_files": successful_files,
        "failed_files": failed_files
    }
    
    return consolidated_result

@app.post("/upload-single-file")
async def upload_single_file(file: UploadFile = File(...)):
    """
    Accept a single file uploaded from UI and call external API
    """
    try:
        # Read file content
        content = await file.read()
        
        # Call external API
        api_result = call_external_api(content, file.filename)
        
        # Prepare response
        response = {
            "message": "File processed",
            "file_info": {
                "filename": file.filename,
                "content_type": file.content_type,
                "size": len(content)
            },
            "api_result": api_result
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file {file.filename}: {str(e)}")

# =================== Supervisor Agent =====================

class SupervisorInput(BaseModel):
    workflow_id: str
    ui_response: str

class WorkflowProceedInput(BaseModel):
    workflow_id: str
    proceed: bool
    qa_input: Optional[QAInput] = None

@app.post("/supervisor-workflow/start")
async def start_supervisor_workflow(files: List[UploadFile] = File(...)):
    """
    Start supervisor workflow: Upload files -> Agent 1 (API) -> Agent 2 (LLM) -> Wait for UI
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    try:
        # Generate workflow ID
        workflow_id = str(uuid.uuid4())
        
        # Read all files first
        file_data = []
        for file in files:
            try:
                content = await file.read()
                file_data.append({
                    "content": content,
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "size": len(content)
                })
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error reading file {file.filename}: {str(e)}")
        
        # Run workflow steps 1 and 2 (Agent 1 -> Agent 2)
        workflow_result = run_workflow_step1_sync(file_data, workflow_id)
        
        # Store workflow state for later use
        store_workflow_state(workflow_id, workflow_result)
        
        return {
            "workflow_id": workflow_id,
            "status": "waiting_for_ui_confirmation",
            "docClassificationAgent_result": workflow_result["docClassificationAgent_result"],
            "rccClassificationAgent_result": workflow_result["rccClassificationAgent_result"],
            "message": "Files processed by DocClassificationAgent (API) and RCCClassificationAgent (LLM). Awaiting UI confirmation to proceed to OnboardingAgent."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supervisor workflow failed: {str(e)}")

@app.post("/supervisor-workflow/proceed")
def proceed_supervisor_workflow(data: WorkflowProceedInput):
    """
    Proceed to Agent 3 after UI confirmation
    """
    try:
        workflow_id = data.workflow_id
        
        # Get previous workflow state
        previous_state = get_workflow_state(workflow_id)
        if not previous_state:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        if not data.proceed:
            # UI decided not to proceed
            delete_workflow_state(workflow_id)
            return {
                "workflow_id": workflow_id,
                "status": "cancelled",
                "message": "Workflow cancelled by UI"
            }
        
        # Prepare UI response with QAInput data
        ui_response = "UI confirmed to proceed with processing"
        qa_data = None
        
        if data.qa_input:
            qa_data = data.qa_input
            ui_response += f" with QAInput data: {qa_data.dict()}"
        
        # Run workflow step 3 (Agent 3)
        final_result = run_workflow_step2(workflow_id, ui_response, previous_state, qa_data)
        
        # Clean up workflow state
        delete_workflow_state(workflow_id)
        
        return {
            "workflow_id": workflow_id,
            "status": final_result["status"],
            "docClassificationAgent_result": final_result["docClassificationAgent_result"],
            "rccClassificationAgent_result": final_result["rccClassificationAgent_result"],
            "onboardingAgent_result": final_result["onboardingAgent_result"],
            "message": final_result["message"],
            "branch_name": final_result.get("branch_name", ""),
            "jira_no": final_result.get("jira_no", "")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow progression failed: {str(e)}")

@app.get("/supervisor-workflow/status/{workflow_id}")
def get_workflow_status(workflow_id: str):
    """
    Get current workflow status
    """
    try:
        workflow_state = get_workflow_state(workflow_id)
        if not workflow_state:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return {
            "workflow_id": workflow_id,
            "status": workflow_state.get("status", "unknown"),
            "current_step": workflow_state.get("current_step", "unknown"),
            "docClassificationAgent_result": workflow_state.get("docClassificationAgent_result", {}),
            "rccClassificationAgent_result": workflow_state.get("rccClassificationAgent_result", {}),
            "onboardingAgent_result": workflow_state.get("onboardingAgent_result", {})
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {str(e)}")

@app.delete("/supervisor-workflow/{workflow_id}")
def cancel_workflow(workflow_id: str):
    """
    Cancel and clean up workflow
    """
    try:
        delete_workflow_state(workflow_id)
        return {
            "workflow_id": workflow_id,
            "status": "cancelled",
            "message": "Workflow cancelled and cleaned up"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel workflow: {str(e)}")