from typing import Dict, List, Any, TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
import operator
from dotenv import load_dotenv
import os
import google.generativeai as genai
import asyncio
import json
import uuid
from submit_on_boarding_service import run_langgraph, QAState
from doc_classification_agent import doc_classification_agent
from rcc_classification_agent import rcc_classification_agent

# Load environment variables
load_dotenv()

# Set up Gemini API
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Define the state structure
class SupervisorState(TypedDict):
    messages: Annotated[List[Dict], add_messages]
    uploaded_files: List[Dict]
    docClassificationAgent_result: Dict[str, Any]
    rccClassificationAgent_result: Dict[str, Any]
    onboardingAgent_result: Dict[str, Any]
    ui_response: str
    current_step: str
    workflow_id: str
    context: Dict[str, Any]
    next_action: str

# Initialize the state
def create_initial_state(uploaded_files: List[Dict], workflow_id: str) -> SupervisorState:
    return {
        "messages": [],
        "uploaded_files": uploaded_files,
        "docClassificationAgent_result": {},
        "rccClassificationAgent_result": {},
        "onboardingAgent_result": {},
        "ui_response": "",
        "current_step": "docClassificationAgent",
        "workflow_id": workflow_id,
        "context": {},
        "next_action": "docClassificationAgent"
    }

# Document Classification Agent: API Service Agent
async def doc_classification_agent_node(state: SupervisorState) -> SupervisorState:
    """Document Classification Agent: Calls external API service to classify uploaded documents"""
    
    uploaded_files = state["uploaded_files"]
    
    # Call the imported document classification agent function
    doc_classification_result = await doc_classification_agent(uploaded_files)
    
    state["docClassificationAgent_result"] = doc_classification_result
    state["current_step"] = "rccClassificationAgent"
    state["next_action"] = "rccClassificationAgent"
    
    return state

# RCC Classification Agent: LLM Processing Agent
def rcc_classification_agent_node(state: SupervisorState) -> SupervisorState:
    """RCC Classification Agent: Uses LLM to analyze document classification results and provide RCC insights"""
    
    docClassificationAgent_result = state["docClassificationAgent_result"]
    
    # Call the imported RCC classification agent function
    rcc_classification_result = rcc_classification_agent(docClassificationAgent_result)
    
    state["rccClassificationAgent_result"] = rcc_classification_result
    state["current_step"] = "wait_for_ui"
    state["next_action"] = "wait_for_ui"
    
    return state

# Submit Onboarding Agent: Onboarding Service Agent
def submit_onboarding_agent_node(state: SupervisorState) -> SupervisorState:
    """Submit Onboarding Agent: Run submit_on_boarding_service with processed data"""
    
    docClassificationAgent_result = state["docClassificationAgent_result"]
    rccClassificationAgent_result = state["rccClassificationAgent_result"]
    ui_response = state["ui_response"]
    
    try:
        # Extract relevant data from previous agents
        uploaded_files = state["uploaded_files"]
        
        # Check if QAInput data is available in the context
        qa_data = state.get("context", {}).get("qa_input")
        
        # Create QAState for the onboarding service
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
        
        # Use QAInput data if available, otherwise extract from other sources
        if qa_data:
            # Use the QAInput data directly
            extracted_data = {
                "answers": qa_data.get("answers", {}),
                "base_branch": qa_data.get("base_branch", "main"),
                "branch_name": qa_data.get("new_branch", f"onboarding-{state['workflow_id']}"),
                "jira_no": qa_data.get("jira_no", "")
            }
        else:
            # Fallback to extraction from other sources
            extracted_data = extract_onboarding_data(docClassificationAgent_result, rccClassificationAgent_result, ui_response, uploaded_files)
        
        # Create QAState for the onboarding service
        qa_state: QAState = {
            "questions": qa_data.get("questions", questions) if qa_data else questions,
            "index": 0,
            "answers": extracted_data.get("answers", {}),
            "command": "",
            "base_branch": extracted_data.get("base_branch", "main"),
            "branch_name": extracted_data.get("branch_name", f"onboarding-{state['workflow_id']}"),
            "jira_no": extracted_data.get("jira_no", ""),
            "sor_codes_content": "",
            "updated_sor_codes": "",
            "rules_content": "",
            "updated_rules": "",
            "bu_on_boarding_content": "",
            "updated_bu_on_boarding": "",
            "abort": False,
            "test_case_report": ""
        }
        
        # Run the onboarding service
        onboarding_result = run_langgraph(qa_state)
        
        # Store the result
        state["onboardingAgent_result"] = {
            "final_status": "completed",
            "final_summary": "Submit onboarding service completed successfully",
            "onboarding_result": onboarding_result,
            "processed_files": [f["filename"] for f in uploaded_files],
            "workflow_id": state["workflow_id"],
            "branch_name": qa_state["branch_name"],
            "jira_no": qa_state["jira_no"]
        }
        
        state["current_step"] = "completed"
        state["next_action"] = "end"
        
    except Exception as e:
        # Handle errors in submit onboarding service
        state["onboardingAgent_result"] = {
            "final_status": "error",
            "final_summary": f"Submit onboarding service failed: {str(e)}",
            "error": str(e),
            "processed_files": [f["filename"] for f in state["uploaded_files"]],
            "workflow_id": state["workflow_id"]
        }
        state["current_step"] = "error"
        state["next_action"] = "end"
    
    return state

def extract_onboarding_data(docClassificationAgent_result: Dict, rccClassificationAgent_result: Dict, ui_response: str, uploaded_files: List[Dict]) -> Dict:
    """Extract onboarding data from previous agent results and UI response"""
    
    extracted_data = {
        "answers": {},
        "base_branch": "main",
        "branch_name": "",
        "jira_no": ""
    }
    
    try:
        # Try to extract data from UI response (assuming it contains onboarding information)
        if ui_response:
            # Parse UI response for onboarding data
            # This is a simplified parser - you may need to customize based on your UI format
            lines = ui_response.split('\n')
            for i, line in enumerate(lines):
                if "onboarding name" in line.lower() or "name:" in line.lower():
                    extracted_data["answers"][0] = line.split(':')[-1].strip()
                elif "partition" in line.lower():
                    extracted_data["answers"][1] = line.split(':')[-1].strip()
                elif "sor codes" in line.lower():
                    extracted_data["answers"][2] = line.split(':')[-1].strip()
                elif "bus unit" in line.lower():
                    extracted_data["answers"][3] = line.split(':')[-1].strip()
                elif "rcc rules" in line.lower():
                    extracted_data["answers"][4] = line.split(':')[-1].strip()
                elif "sampling rule ref" in line.lower():
                    extracted_data["answers"][5] = line.split(':')[-1].strip()
                elif "sampling id" in line.lower():
                    extracted_data["answers"][6] = line.split(':')[-1].strip()
                elif "sampling data" in line.lower():
                    extracted_data["answers"][7] = line.split(':')[-1].strip()
                elif "branch" in line.lower():
                    extracted_data["branch_name"] = line.split(':')[-1].strip()
                elif "jira" in line.lower():
                    extracted_data["jira_no"] = line.split(':')[-1].strip()
        
        # If no data extracted from UI, try to extract from agent results
        if not extracted_data["answers"]:
            # Extract from Document Classification Agent results (API service results)
            if docClassificationAgent_result and "results" in docClassificationAgent_result:
                for result in docClassificationAgent_result["results"]:
                    if result.get("status") == "success" and "api_response" in result:
                        # Try to extract onboarding data from API response
                        api_response = result["api_response"]
                        if isinstance(api_response, dict):
                            # Extract relevant fields from API response
                            pass  # Customize based on your API response structure
        
        # If still no data, create default values
        if not extracted_data["answers"]:
            extracted_data["answers"] = {
                0: f"Onboarding-{uuid.uuid4().hex[:8]}",
                1: "P0",
                2: "ACCT/SOR,DEAL/SOR",
                3: "DEFAULT_BU",
                4: "DEFAULT_RCC_RULES",
                5: "DEFAULT_SAMPLING_REF",
                6: "DEFAULT_SAMPLING_ID",
                7: "DEFAULT_SAMPLING_DATA"
            }
        
        # Generate branch name if not provided
        if not extracted_data["branch_name"]:
            onboarding_name = extracted_data["answers"].get(0, "onboarding")
            extracted_data["branch_name"] = f"onboarding-{onboarding_name}-{uuid.uuid4().hex[:8]}"
        
        # Generate JIRA number if not provided
        if not extracted_data["jira_no"]:
            extracted_data["jira_no"] = f"JIRA-{uuid.uuid4().hex[:8]}"
            
    except Exception as e:
        print(f"Error extracting onboarding data: {e}")
        # Provide default values
        extracted_data["answers"] = {
            0: f"Onboarding-{uuid.uuid4().hex[:8]}",
            1: "P0",
            2: "ACCT/SOR,DEAL/SOR",
            3: "DEFAULT_BU",
            4: "DEFAULT_RCC_RULES",
            5: "DEFAULT_SAMPLING_REF",
            6: "DEFAULT_SAMPLING_ID",
            7: "DEFAULT_SAMPLING_DATA"
        }
        extracted_data["branch_name"] = f"onboarding-{uuid.uuid4().hex[:8]}"
        extracted_data["jira_no"] = f"JIRA-{uuid.uuid4().hex[:8]}"
    
    return extracted_data



# Routing function for LangGraph
def route_workflow(state: SupervisorState) -> Literal["docClassificationAgent", "rccClassificationAgent", "onboardingAgent", "wait_for_ui", "end", END]:
    """Route to the appropriate agent based on current step"""
    next_action = state.get("next_action", "docClassificationAgent")
    
    if next_action == "docClassificationAgent":
        return "docClassificationAgent"
    elif next_action == "rccClassificationAgent":
        return "rccClassificationAgent"
    elif next_action == "onboardingAgent":
        return "onboardingAgent"
    elif next_action == "wait_for_ui":
        return "wait_for_ui"
    elif next_action == "end":
        return END
    else:
        return "wait_for_ui"

# Wait for UI function
def wait_for_ui(state: SupervisorState) -> SupervisorState:
    """Wait for UI response - this is a placeholder that maintains state"""
    # This function just maintains the state while waiting for UI
    # The actual UI interaction happens through the API endpoints
    return state

# Create the LangGraph workflow
def create_supervisor_workflow():
    """Create the supervisor workflow using LangGraph"""
    
    # Create the graph
    workflow = StateGraph(SupervisorState)
    
    # Add nodes
    workflow.add_node("docClassificationAgent", doc_classification_agent_node)
    workflow.add_node("rccClassificationAgent", rcc_classification_agent_node)
    workflow.add_node("onboardingAgent", submit_onboarding_agent_node)
    workflow.add_node("wait_for_ui", wait_for_ui)
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "docClassificationAgent",
        route_workflow,
        {
            "rccClassificationAgent": "rccClassificationAgent",
            "wait_for_ui": "wait_for_ui",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "rccClassificationAgent",
        route_workflow,
        {
            "onboardingAgent": "onboardingAgent",
            "wait_for_ui": "wait_for_ui",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "onboardingAgent",
        route_workflow,
        {
            "wait_for_ui": "wait_for_ui",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "wait_for_ui",
        route_workflow,
        {
            "onboardingAgent": "onboardingAgent",
            "end": END
        }
    )
    
    # Set entry point
    workflow.set_entry_point("docClassificationAgent")
    
    # Compile the graph
    app = workflow.compile(checkpointer=MemorySaver())
    
    return app

# Workflow management functions
def run_workflow_step1(uploaded_files: List[Dict], workflow_id: str) -> Dict[str, Any]:
    """Run workflow steps 1 and 2 (Agent 1 -> Agent 2) using LangGraph"""
    
    # Create initial state
    state = create_initial_state(uploaded_files, workflow_id)
    
    # Create and run the workflow
    app = create_supervisor_workflow()
    
    # Run the workflow up to wait_for_ui
    config = {"configurable": {"thread_id": workflow_id}}
    
    # Run the workflow
    result = app.invoke(state, config=config)
    
    return {
        "workflow_id": workflow_id,
        "current_step": result["current_step"],
        "docClassificationAgent_result": result["docClassificationAgent_result"],
        "rccClassificationAgent_result": result["rccClassificationAgent_result"],
        "status": "waiting_for_ui_confirmation",
        "thread_id": workflow_id
    }

def run_workflow_step2(workflow_id: str, ui_response: str, previous_state: Dict[str, Any], qa_data: Optional[Dict] = None) -> Dict[str, Any]:
    """Run workflow step 3 (Submit Onboarding Agent) after UI confirmation using LangGraph"""
    
    # Create the workflow app
    app = create_supervisor_workflow()
    
    # Update the state with UI response and QAInput data
    state = {
        "messages": [],
        "uploaded_files": previous_state.get("uploaded_files", []),
        "docClassificationAgent_result": previous_state.get("docClassificationAgent_result", {}),
        "rccClassificationAgent_result": previous_state.get("rccClassificationAgent_result", {}),
        "onboardingAgent_result": {},
        "ui_response": ui_response,
        "current_step": "onboardingAgent",
        "workflow_id": workflow_id,
        "context": {"qa_input": qa_data} if qa_data else {},
        "next_action": "onboardingAgent"
    }
    
    # Run the workflow from submit onboarding agent
    config = {"configurable": {"thread_id": workflow_id}}
    
    # Create a new graph starting from submit onboarding agent
    workflow = StateGraph(SupervisorState)
    workflow.add_node("onboardingAgent", submit_onboarding_agent_node)
    workflow.add_edge("onboardingAgent", END)
    workflow.set_entry_point("onboardingAgent")
    
    final_app = workflow.compile(checkpointer=MemorySaver())
    result = final_app.invoke(state, config=config)
    
    # Check if submit onboarding service completed successfully
    onboardingAgent_result = result["onboardingAgent_result"]
    if onboardingAgent_result.get("final_status") == "completed":
        status = "completed"
        message = "Submit onboarding service completed successfully"
    elif onboardingAgent_result.get("final_status") == "error":
        status = "error"
        message = f"Submit onboarding service failed: {onboardingAgent_result.get('final_summary', 'Unknown error')}"
    else:
        status = "unknown"
        message = "Submit onboarding service status unknown"
    
    return {
        "workflow_id": workflow_id,
        "current_step": result["current_step"],
        "docClassificationAgent_result": result["docClassificationAgent_result"],
        "rccClassificationAgent_result": result["rccClassificationAgent_result"],
        "onboardingAgent_result": result["onboardingAgent_result"],
        "status": status,
        "message": message,
        "branch_name": onboardingAgent_result.get("branch_name", ""),
        "jira_no": onboardingAgent_result.get("jira_no", "")
    }

# In-memory storage for workflow states (for API endpoints)
workflow_states = {}

def store_workflow_state(workflow_id: str, state: Dict[str, Any]):
    """Store workflow state in memory"""
    workflow_states[workflow_id] = state

def get_workflow_state(workflow_id: str) -> Dict[str, Any]:
    """Get workflow state from memory"""
    return workflow_states.get(workflow_id, {})

def delete_workflow_state(workflow_id: str):
    """Delete workflow state from memory"""
    if workflow_id in workflow_states:
        del workflow_states[workflow_id]

# Function to get workflow status from LangGraph checkpoint
def get_workflow_status_from_langgraph(thread_id: str) -> Dict[str, Any]:
    """Get workflow status from LangGraph checkpoint"""
    try:
        app = create_supervisor_workflow()
        config = {"configurable": {"thread_id": thread_id}}
        
        # Get the current state from the checkpoint
        # Note: This is a simplified approach. In a real implementation,
        # you would use LangGraph's checkpoint retrieval methods
        return {
            "thread_id": thread_id,
            "status": "active",
            "message": "Workflow is active in LangGraph"
        }
    except Exception as e:
        return {
            "thread_id": thread_id,
            "status": "error",
            "error": str(e)
        } 