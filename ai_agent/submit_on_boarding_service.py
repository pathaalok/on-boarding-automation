from dotenv import load_dotenv
import os
from github import Github
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Dict
import re
from openai import OpenAI
import requests
from requests.auth import HTTPBasicAuth
import asyncio
import google.generativeai as genai

# Load environment variables
load_dotenv()

# --- Define State Schema ---
class QAState(TypedDict):
    questions: List[str]
    index: int
    answers: Dict[int, str]
    command: str
    branch_name: str
    base_branch: str
    jira_no: str
    sor_codes_content: str
    updated_sor_codes: str
    rules_content: str
    updated_rules: str
    bu_on_boarding_content: str
    updated_bu_on_boarding: str
    abort: bool
    test_case_report: str

model = os.getenv("MODEL")

# Set OpenAI API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- GitHub Setup ---
g = Github(os.getenv("GITHUB_TOKEN"))
repo = g.get_repo(os.getenv("GITHUB_REPO"))
app_admin_service_url = os.getenv("APP_ADMIN_SERVICE_URL") 
app_service_name = os.getenv("APP_SERVICE_NAME") 

sor_code_file = os.getenv("SOR_CODES_YML") 
rule_file = os.getenv("RULES_YML") 
bu_on_boarding_file = os.getenv("BU_ON_BOARDING_YML")

test_url = os.getenv("TEST_CASES_URL")

# Queue for SSE
event_queue = asyncio.Queue() 

async def event_stream():
    while True:
        data = await event_queue.get()
        yield f"data: {data}\n\n"
        event_queue.task_done()

async def notify(message):
    await event_queue.put(message)

def stream_message_to_ui(message: str,type: str="msg",extraText: str =""):
    t = {
            'message' : message,
            'type' : type,
            'extraText' : extraText
        }
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(notify(t))
    except RuntimeError:
        # Fallback if not in an event loop (e.g., running in sync context)
        asyncio.run(notify(t))

# --- GitHub Helpers ---
def check_if_branch_exists(branch_name: str) -> bool:
    try:
        repo.get_branch(branch_name)
        return True
    except:
        return False

def create_base_branch(state: QAState) -> QAState:
    create_base_branch_if_not_exists(state)
    return state

def create_base_branch_if_not_exists(state: QAState) -> str:
    base_branch = state.get("base_branch").strip()
    if not check_if_branch_exists(base_branch):
        default_branch = repo.get_branch(repo.default_branch)
        repo.create_git_ref(ref=f"refs/heads/{base_branch}", sha=default_branch.commit.sha)
        print(f"Created base branch: {base_branch}")
        stream_message_to_ui(f"Created base branch: {base_branch}","msg")
    else:
        print(f"base branch '{base_branch}' already exists.")
        stream_message_to_ui(f"base branch {base_branch} already exists.")
    return base_branch

def create_on_boarding_branch_if_not_exists(state: QAState,base_branch: str) -> str:
    print(f"base branch '{base_branch}'")
    new_branch_name = state.get("branch_name").strip()
    if not check_if_branch_exists(new_branch_name):
        base_branch_1 = repo.get_branch(base_branch)
        repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=base_branch_1.commit.sha)
        print(f"Created on-boarding branch: {new_branch_name} from {base_branch}")
        stream_message_to_ui(f"Created on-boarding branch: {new_branch_name} from {base_branch}")
    else:
        print(f"Branch '{new_branch_name}' already exists.")
        stream_message_to_ui(f"Branch {new_branch_name} already exists.")
    return new_branch_name

def check_if_pr_exists(new_branch_name: str,base_branch :str) -> bool:
    open_prs = repo.get_pulls(state="open", base=base_branch)
    for pr in open_prs:
        if pr.head.ref == new_branch_name:
            print(f"A PR from branch '{new_branch_name}' already exists.")
            return True
    return False

def create_pull_request(new_branch_name: str,base_branch: str,jira_no: str):
    pr_title = f"{jira_no} Submit On-boarding Details"
    pr_body = f"Pull request contains the onboarding details for {jira_no}"
    print(f"base branch '{base_branch}'")
    if not check_if_pr_exists(new_branch_name,base_branch):
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=new_branch_name,
            base=base_branch
        )
        print(f"Created PR: {pr.html_url}")
        stream_message_to_ui(f"Created PR: {pr.html_url}")
    else:
        print(f"Skipping PR creation because one already exists.")
        stream_message_to_ui(f"Skipping PR creation because one already exists.")

# --- File Helpers ---
def fetch_content(branch_name: str,file_path: str) -> str:
    try:
        file = repo.get_contents(file_path, ref=branch_name)
        return file.decoded_content.decode()
    except Exception as e:
        print(f"Error fetching onboarding file: {e}")
        return ""

def update_or_create_file(updated_content: str, branch_name: str,file_path:str,jira_no:str):
    commit_message = f"{jira_no} Update {file_path} with LLM-generated content"
    try:
        file = repo.get_contents(file_path, ref=branch_name)
        file_sha = file.sha
        repo.update_file(file_path, commit_message, updated_content, file_sha, branch=branch_name)
        print(f"Updated {file_path} in branch {branch_name}")
        stream_message_to_ui(f"Updated {file_path} in {branch_name} branch")
    except Exception as e:
        print(f"Error updating {file_path}: {e}")


def extract_format_content(text: str, format: str) -> str:
    pattern = rf"```{re.escape(format)}(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return text.strip()

# --- OPEN AI LLM Helpers ---
def call_openai(system_prompt: str, user_prompt: str,format :str) -> str:
   
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    raw_content = response.choices[0].message.content
    yaml_content = extract_format_content(raw_content,format)
    return yaml_content

# --- GEMINI AI LLM Helpers ---

def call_gemini(system_prompt: str, user_prompt: str,format :str) -> str:
   
    full_prompt = f"{system_prompt.strip()}\n\n{user_prompt.strip()}"

    print(full_prompt)

    model = genai.GenerativeModel("gemini-1.5-flash")

    response = model.generate_content(full_prompt)
    return extract_format_content(response.text,format)

# --- LLM Helpers ---
def call_ai_model(system_prompt: str, user_prompt: str,format: str) -> str:

    if model == "GEMINI":
        return call_gemini(system_prompt,user_prompt,format)
    else:
        return call_openai(system_prompt,user_prompt,format)


def build_user_prompt(state: dict) -> str:
    print(state)
    prompt_parts = ["INPUT DATA:"]
    for i, question in enumerate(state["questions"]):
        answer = state["answers"].get(i)
        if answer is None:
            answer = state["answers"].get(str(i), "(no answer)")
        prompt_parts.append(f"Q{i+1}: {question}\nA{i+1}: {answer}")
    return "\n\n".join(prompt_parts)


# Split Submit Nodes

def create_on_boarding_branch(state: QAState) -> QAState:
    base_branch = state.get("base_branch")
    create_on_boarding_branch_if_not_exists(state,base_branch)
    return state 

def fetch_sor_codes(state: QAState) -> QAState:
    branch_name = state.get("branch_name")
    sor_codes_content = fetch_content(branch_name,sor_code_file)
    if not sor_codes_content:
        print(f"Failed to fetch {sor_code_file}")
        stream_message_to_ui(f"Failed to fetch {sor_code_file}")
        state["abort"] = True
    else:
        state["sor_codes_content"] = sor_codes_content
    return state

def call_llm_for_sor_codes(state: QAState) -> QAState:

    system_prompt = f"""
        You are an expert onboarding assistant. You are provided with a Acct,Deal SOR configurations.
        You must:
        - extract only the SOR from given input format ACCT/SOR_CODE,DEAL/SOR_CODE check case in-sensitive
        - Check whether a given SOR is present in Acct or DEAL respectively.
        - If not present, update it in the respective section
        - Do not add any new sections from INPUT DATA
        - Maintain the structure and return the updated YAML.
         
        \n\n{state["sor_codes_content"]}
    """
    user_prompt = build_user_prompt(state)
    updated_sor_codes = call_ai_model(system_prompt, user_prompt,"yaml")
    print(f"updated_sor_codes YAML.")
    stream_message_to_ui(f"updated sor_codes from AI Model.")
    state["updated_sor_codes"] = updated_sor_codes
    return state

def update_sor_codes_file_node(state: QAState) -> QAState:
    branch_name = state.get("branch_name")
    update_or_create_file(state["updated_sor_codes"], branch_name,sor_code_file,state["jira_no"])
    return state

def fetch_rules(state: QAState) -> QAState:
    branch_name = state.get("branch_name")
    rules_content = fetch_content(branch_name,rule_file)
    if not rules_content:
        print(f"Failed to fetch {rule_file}")
        stream_message_to_ui(f"Failed to fetch {rule_file}")
        state["abort"] = True
    else:
        state["rules_content"] = rules_content
    return state

def call_llm_for_rules(state: QAState) -> QAState:

    system_prompt = f"""
        You are an expert onboarding assistant. You are provided with a YAML configuration that contains rules configuration based on below rule types

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
        - Check whether a given key input for that section is already present if yes dont do any action
        - If not present, update it in the respective section which are more matched with columns based on "RCC RULES" INPUT DATA provided
        - if value is not present for any column in above matched keep '' instead of null
        - Do not add any new sections from INPUT DATA
        - key for each section should not contain duplicate
        - Maintain the structure and return the updated YAML.
        
        \n\n{state["rules_content"]}
    """
    user_prompt = build_user_prompt(state)
    updated_rules = call_ai_model(system_prompt, user_prompt,"yaml")
    print(" updated_rules YAML.")
    stream_message_to_ui(" updated rules YAML from AI Model.")
    state["updated_rules"] = updated_rules
    return state

def update_rules_file_node(state: QAState) -> QAState: 
    branch_name = state.get("branch_name")
    update_or_create_file(state["updated_rules"], branch_name,rule_file,state["jira_no"])
    return state

# 


def fetch_bu_on_boarding(state: QAState) -> QAState:
    branch_name = state.get("branch_name")
    bu_on_boarding_content = fetch_content(branch_name,bu_on_boarding_file)
    if not bu_on_boarding_content:
        print(f"Failed to fetch {bu_on_boarding_file}")
        stream_message_to_ui(f"Failed to fetch {bu_on_boarding_file}")
        state["abort"] = True
    else:
        state["bu_on_boarding_content"] = bu_on_boarding_content
    return state

def call_llm_for_bu_on_boarding(state: QAState) -> QAState:

    system_prompt = f"""
       You are an expert onboarding assistant. You are provided with a YAML configuration that contains onboarding configuration

        ------------------------------------------------------
        Sample of the struture

        busUnitOnBoardingCongif: # Key is the BUS_UNIT
            BU_UNIT:
                contentRepoRef: # Is a Array based on given Partition (example "Partition"_OS1)
                    - "Partition"_OS1
                dispositionConfig:
                    enableDeleteNotification: # true if it is Regulated
                    enableCaseNOtification: # true if it is Regulated
                    notificationRecipts: abc@test.com
                SamplingConfig: # Is a Array
                    - ruleRef : # AUTO_APPROVE if non Regulated, if not consider "Sampling Rule Ref" from INPUT DATA
                    sampling:
                        id: # based on "Sampling Id" from INPUT DATA
                        values: # list base on "Sampling Data" from INPUT DATA
                    
        ------------------------------------------------------

        Partions:
            P0 is Federated
            P1 to P4 are non Regulated
            P5 is Regulated
        
        You must:
        - Check whether a given Bus Unit input for that section is already present do not override but update respective section with given INPUT DATA
        - If not present, Create new section based on sample provided
        - For SamplingConfig , if already present for Bus Unit check ruleRef also if present append to it if not create new with INPUT DATA
        - Maintain the structure and return the updated YAML.
    
        
        Current DATA

        \n\n{state["bu_on_boarding_content"]}
    """
    user_prompt = build_user_prompt(state)
    updated_bu_on_boarding = call_ai_model(system_prompt, user_prompt,"yaml")
    print(" updated bu_on_boarding YAML.")
    stream_message_to_ui(" updated BU ON BOARDING YAML from AI Model.")
    state["updated_bu_on_boarding"] = updated_bu_on_boarding
    return state

def update_bu_on_boarding_node(state: QAState) -> QAState: 
    branch_name = state.get("branch_name")
    update_or_create_file(state["updated_bu_on_boarding"], branch_name,bu_on_boarding_file,state["jira_no"])
    return state
# 

def create_pr_node(state: QAState) -> QAState:
    branch_name = state.get("branch_name")
    base_branch = state.get("base_branch")
    jira_no = state.get("jira_no")
    create_pull_request(branch_name,base_branch,jira_no)
    return state

def call_api_to_app(state: QAState,app_url : str):
    
    branch_name = state["branch_name"]
    app_total_url = f"{app_url}change-branch?branch={branch_name}"
    try:
        response = requests.post(app_total_url, None)
        response.raise_for_status()
        print(f"API call {app_total_url} successful: {response.status_code}")
        stream_message_to_ui(f"updated new config in {app_url} from branch {branch_name}")
    except Exception as e:
        print(f"API call {app_total_url} failed: {e}")
        stream_message_to_ui(f"API call {app_total_url} failed")

def call_api_to_update_config(state: QAState) -> QAState:

    admin_url = f"{app_admin_service_url}/instances"
    print("admin_url:", admin_url)

    try:
        # Add basic authentication credentials
        response = requests.get(
            admin_url,
            auth=HTTPBasicAuth("admin", "adminpassword")  
        )
        response.raise_for_status()
        instances = response.json()

        # Extract service URLs for matching appName
        matching_urls = [
            registration["serviceUrl"]
            for instance in instances
            if (registration := instance.get("registration"))
            and registration.get("name", "").lower() == app_service_name.lower()
        ]

        print("Matching instance URLs:", matching_urls)

        for url in matching_urls:
            try:
                call_api_to_app(state, url)
                print(f"Successfully notified {url}")
            except Exception as notify_err:
                print(f"Failed to notify {url}: {notify_err}")
                stream_message_to_ui(f"Failed to notify {url}")

    except Exception as e:
        print(f"Error fetching instances: {e}")

    return state

def call_api_to_trigger_test_cases(state: QAState) -> QAState:

    admin_url = f"{app_admin_service_url}/instances"
    print("admin_url:", admin_url)

    response = requests.get(
            admin_url,
            auth=HTTPBasicAuth("admin", "adminpassword")  
        )
    response.raise_for_status()
    instances = response.json()

        # Extract service URLs for matching appName
    matching_urls = [
            registration["serviceUrl"]
            for instance in instances
            if (registration := instance.get("registration"))
            and registration.get("name", "").lower() == app_service_name.lower()
    ]

    print("Matching instance URLs:", matching_urls)

    test_case_url = f"{matching_urls[0]}{test_url}"
    print("test_case_url:", test_case_url)
    stream_message_to_ui("Test Cases execution inprogess")
    try:
        # Add basic authentication credentials
        response = requests.get(
            test_case_url,
            auth=HTTPBasicAuth("admin", "adminpassword")  
        )
        response.raise_for_status()
        response_text =  response.text
        stream_message_to_ui("Test Cases executed")
        state["test_case_report"]  = response_text

    except Exception as e:
        print(f"Error fetching instances: {e}")
        stream_message_to_ui("Test Cases execution failed")

    return state




# --- LangGraph Flow ---


graph = StateGraph(QAState)


# Submit split nodes
graph.add_node("create_base_branch", create_base_branch)
graph.add_node("create_on_boarding_branch", create_on_boarding_branch)

graph.add_node("fetch_sor_codes", fetch_sor_codes)
graph.add_node("call_llm_for_sor_codes", call_llm_for_sor_codes)
graph.add_node("update_sor_codes_file", update_sor_codes_file_node)

graph.add_node("fetch_rules", fetch_rules)
graph.add_node("call_llm_for_rules", call_llm_for_rules)
graph.add_node("update_rules_file", update_rules_file_node)

graph.add_node("fetch_bu_on_boarding", fetch_bu_on_boarding)
graph.add_node("call_llm_for_bu_on_boarding", call_llm_for_bu_on_boarding)
graph.add_node("update_bu_on_boarding_file", update_bu_on_boarding_node)

graph.add_node("create_pr", create_pr_node)

graph.add_node("call_api_to_update_config", call_api_to_update_config)

graph.add_node("call_api_to_trigger_test_cases", call_api_to_trigger_test_cases)

graph.add_edge(START, "create_base_branch")


# Submit Chain

graph.add_edge("create_base_branch", "create_on_boarding_branch")

graph.add_edge("create_on_boarding_branch", "fetch_sor_codes")
graph.add_edge("fetch_sor_codes", "call_llm_for_sor_codes")
graph.add_edge("call_llm_for_sor_codes", "update_sor_codes_file")

graph.add_edge("update_sor_codes_file", "fetch_rules")
graph.add_edge("fetch_rules", "call_llm_for_rules")
graph.add_edge("call_llm_for_rules", "update_rules_file")

graph.add_edge("update_rules_file", "fetch_bu_on_boarding")
graph.add_edge("fetch_bu_on_boarding", "call_llm_for_bu_on_boarding")
graph.add_edge("call_llm_for_bu_on_boarding", "update_bu_on_boarding_file")

# enable this without LLM call just to test flow
# graph.add_edge("create_on_boarding_branch", "fetch_rules")
# graph.add_edge("fetch_rules", "update_rules_file")
# enable this without LLM call just to test flow

graph.add_edge("update_bu_on_boarding_file", "create_pr")
graph.add_edge("create_pr", "call_api_to_update_config")
graph.add_edge("call_api_to_update_config", "call_api_to_trigger_test_cases")

graph.add_edge("call_api_to_trigger_test_cases", END)

def run_langgraph(state: QAState):
    compiled_graph = graph.compile()
    return compiled_graph.invoke(state)