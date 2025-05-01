from dotenv import load_dotenv
import os
from github import Github
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Dict
import re
from openai import OpenAI
import requests

# Load environment variables
load_dotenv()

# --- Define State Schema ---
class QAState(TypedDict):
    questions: List[str]
    index: int
    answers: Dict[int, str]
    command: str
    branch_name: str
    target_branch: str
    sor_codes_content: str
    updated_sor_codes: str
    rules_content: str
    updated_rules: str
    abort: bool

# Set OpenAI API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Load Questions ---
with open("questions.txt", "r") as f:
    questions = [line.strip() for line in f if line.strip()]

# --- Initial State ---
initial_state: QAState = {
    "questions": questions,
    "index": 0,
    "answers": {},
    "command": "",
    "target_branch":"",
    "branch_name": "",
    "sor_codes_content": "",
    "updated_sor_codes": "",
    "rules_content":"",
    "updated_rules": "",
    "abort": False
}

# --- GitHub Setup ---
g = Github(os.getenv("GITHUB_TOKEN"))
repo = g.get_repo(os.getenv("GITHUB_REPO"))
app_conf_change_url = os.getenv("APPLICATION_CONFIG_CHANGE_URL") 

# --- GitHub Helpers ---
def check_if_branch_exists(branch_name: str) -> bool:
    try:
        repo.get_branch(branch_name)
        return True
    except:
        return False

def create_target_branch_if_not_exists() -> str:
    target_branch =  input("Enter target branch to create new branch : ").strip()
    if not check_if_branch_exists(target_branch):
        default_branch = repo.get_branch(repo.default_branch)
        repo.create_git_ref(ref=f"refs/heads/{target_branch}", sha=default_branch.commit.sha)
        print(f"Created target branch: {target_branch}")
    else:
        print(f"Target branch '{target_branch}' already exists.")
    return target_branch

def create_on_boarding_branch_if_not_exists(target_branch: str) -> str:
    print(f"Target branch '{target_branch}'")
    new_branch_name =  input("Enter new on-boarding branch: ").strip()
    if not check_if_branch_exists(new_branch_name):
        target_branch_1 = repo.get_branch(target_branch)
        repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=target_branch_1.commit.sha)
        print(f"Created on-boarding branch: {new_branch_name} from {target_branch}")
    else:
        print(f"Branch '{new_branch_name}' already exists.")
    return new_branch_name

def check_if_pr_exists(new_branch_name: str,target_branch :str) -> bool:
    open_prs = repo.get_pulls(state="open", base=target_branch)
    for pr in open_prs:
        if pr.head.ref == new_branch_name:
            print(f"A PR from branch '{new_branch_name}' already exists.")
            return True
    return False

def create_pull_request(new_branch_name: str,target_branch: str):
    pr_title = "Submit On-boarding Details"
    pr_body = "This pull request contains the onboarding details."
    print(f"Target branch '{target_branch}'")
    if not check_if_pr_exists(new_branch_name,target_branch):
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=new_branch_name,
            base=target_branch
        )
        print(f"Created PR: {pr.html_url}")
    else:
        print(f"Skipping PR creation because one already exists.")

# --- File Helpers ---
def fetch_content(branch_name: str,file_path: str) -> str:
    try:
        file = repo.get_contents(file_path, ref=branch_name)
        return file.decoded_content.decode()
    except Exception as e:
        print(f"Error fetching onboarding file: {e}")
        return ""

def update_or_create_file(updated_content: str, branch_name: str,file_path:str):
    commit_message = f"Update {file_path} with LLM-generated content"
    try:
        file = repo.get_contents(file_path, ref=branch_name)
        file_sha = file.sha
        repo.update_file(file_path, commit_message, updated_content, file_sha, branch=branch_name)
        print(f"Updated {file_path} in branch {branch_name}")
    except Exception as e:
        print(f"Error updating {file_path}: {e}")

def extract_yaml_content(text: str) -> str:
    yaml_match = re.search(r"```yaml(.*?)```", text, re.DOTALL)
    if yaml_match:
        return yaml_match.group(1).strip()
    else:
        return text.strip()

# --- LLM Helpers ---
def call_openai(system_prompt: str, user_prompt: str) -> str:
    print(f"system_prompt {system_prompt}")
    print(f"user_prompt {user_prompt}")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    raw_content = response.choices[0].message.content
    yaml_content = extract_yaml_content(raw_content)
    return yaml_content

def build_user_prompt(state: QAState) -> str:
    prompt_parts = []
    for i, question in enumerate(state["questions"]):
        answer = state["answers"].get(i, "(no answer)")
        prompt_parts.append(f"Q{i+1}: {question}\nA{i+1}: {answer}")
    return "\n\n".join(prompt_parts)

# --- LangGraph Nodes ---

def ask_question(state: QAState) -> QAState:

    if state == {} :
        state = initial_state 

    idx = state["index"]
    question = state["questions"][idx]
    prev_answer = state["answers"].get(idx, "")
    prompt = f"\nQ{idx + 1}: {question}\n"
    if prev_answer:
        prompt += f"(Press Enter to keep previous answer: \"{prev_answer}\")\n"
    answer = input(prompt + "Your answer: ").strip()
    if not answer and prev_answer:
        answer = prev_answer
    state["answers"][idx] = answer
    return state

def handle_command(state: QAState) -> QAState:
    idx = state["index"]
    last = len(state["questions"]) - 1
    if idx == last:
        cmd = input("You've answered all questions. Type 'preview', 'submit', 'end', or 'goto <n>': ").strip().lower()
    else:
        cmd = input("Enter command (next / prev / preview / goto / submit / end): ").strip().lower()
    state["command"] = cmd
    if cmd == "next" and idx < last:
        state["index"] += 1
    elif cmd == "prev" and idx > 0:
        state["index"] -= 1
    elif cmd.startswith("goto"):
        match = re.match(r"goto\s+(\d+)", cmd)
        if match:
            target = int(match.group(1)) - 1
            if 0 <= target <= last:
                state["index"] = target
                state["command"] = "goto"
            else:
                print("Invalid question number.")
                state["command"] = "preview"
    elif cmd == "end":
        state["command"] = "end"
    return state

def preview_answers(state: QAState) -> QAState:
    print("\n=== Preview Answers ===")
    for i, question in enumerate(state["questions"]):
        print(f"Q{i + 1}: {question}")
        print(f"A{i + 1}: {state['answers'].get(i, '(no answer)')}\n")
    return state

# Split Submit Nodes
def create_target_branch(state: QAState) -> QAState:
    target_branch = create_target_branch_if_not_exists()
    state["target_branch"] = target_branch
    return state

def create_on_boarding_branch(state: QAState) -> QAState:
    target_branch = state.get("target_branch")
    branch_name = create_on_boarding_branch_if_not_exists(target_branch)
    state["branch_name"] = branch_name
    return state 

def fetch_sorCodes(state: QAState) -> QAState:
    branch_name = state.get("branch_name")
    sor_codes_content = fetch_content(branch_name,"on-board.yml")
    if not sor_codes_content:
        print("Failed to fetch onboarding.yml.")
        state["abort"] = True
    else:
        state["sor_codes_content"] = sor_codes_content
    return state

def update_sor_codes_yaml(state: QAState) -> QAState:
    if state.get("abort"):
        return state

    system_prompt = f"""
        You are an expert onboarding assistant. You are provided with a Acct,Deal SOR configurations.
        You must:
        - extract only the SOR from given input format  (Acct/SOR or Deal/SOR) check case sensitive
        - Check whether a given SOR is present in Acct or DEAL respectively.
        - If not present, update it in the respective section.
        - Do not create any new sections
        - Maintain the structure and return the updated YAML.
         
        \n\n{state["sor_codes_content"]}
    """
    user_prompt = build_user_prompt(state)
    updated_sor_codes = call_openai(system_prompt, user_prompt)
    print(f"Generated updated_sor_codes YAML.")
    state["updated_sor_codes"] = updated_sor_codes
    return state

def update_sor_codes_file_node(state: QAState) -> QAState: 
    if state.get("abort"):
        return state
    branch_name = state.get("branch_name")
    update_or_create_file(state["updated_sor_codes"], branch_name,"on-board.yml")
    return state

def fetch_rules(state: QAState) -> QAState:
    branch_name = state.get("branch_name")
    rules_content = fetch_content(branch_name,"rules.yml")
    if not rules_content:
        print("Failed to fetch rules.yml.")
        state["abort"] = True
    else:
        state["rules_content"] = rules_content
    return state

def update_rules_yaml(state: QAState) -> QAState:
    if state.get("abort"):
        return state

    system_prompt = f"""
        You are an expert onboarding assistant. You are provided with a YAML configuration that contains rules configuration based on rule types non_regulated_rccRule,inv_ref_id_rccRule,non_regulated_inv_ref_id_rccRule
 
        Partions:
            P0 is Federated
            P1 to P4 are non Regulated
        
        You must:
        - Check whether a given key input for that section is already present if yes dont do any action
        - If not present, update it in the respective section based on input data provided
        - key for each section should not contain duplicate
        - Maintain the structure and return the updated YAML.
        
        \n\n{state["rules_content"]}
    """
    user_prompt = build_user_prompt(state)
    updated_rules = call_openai(system_prompt, user_prompt)
    print(f"Generated updated_rules YAML.")
    state["updated_rules"] = updated_rules
    return state

def update_rules_file_node(state: QAState) -> QAState: 
    if state.get("abort"):
        return state
    branch_name = state.get("branch_name")
    update_or_create_file(state["updated_rules"], branch_name,"rules.yml")
    return state

def create_pr_node(state: QAState) -> QAState:
    if state.get("abort"):
        return state
    branch_name = state.get("branch_name")
    target_branch = state.get("target_branch")
    create_pull_request(branch_name,target_branch)
    return state

def call_api_to_update_config(state: QAState) -> QAState:
    if state.get("abort"):
        return state

    try:
        response = requests.post(app_conf_change_url+state["branch_name"], None)
        response.raise_for_status()
        print(f"API call successful: {response.status_code}")
    except Exception as e:
        print(f"API call failed: {e}")

    return state

# --- LangGraph Flow ---
def get_next_node(state: QAState) -> str:
    cmd = state["command"]
    if cmd == "submit":
        return "submit"
    elif cmd == "preview":
        return "preview"
    elif cmd in {"next", "prev", "goto"}:
        return "ask"
    elif cmd == "end":
        return END
    else:
        return "route"

graph = StateGraph(QAState)

graph.add_node("ask", ask_question)
graph.add_node("route", handle_command)
graph.add_node("preview", preview_answers)

# Submit split nodes
graph.add_node("create_target_branch", create_target_branch)
graph.add_node("create_on_boarding_branch", create_on_boarding_branch)

graph.add_node("fetch_sorCodes", fetch_sorCodes)
graph.add_node("update_sor_codes_yaml", update_sor_codes_yaml)
graph.add_node("update_sor_codes_file", update_sor_codes_file_node)

graph.add_node("fetch_rules", fetch_rules)
graph.add_node("update_rules_yaml", update_rules_yaml)
graph.add_node("update_rules_file", update_rules_file_node)

graph.add_node("create_pr", create_pr_node)

graph.add_node("call_api_to_update_config", call_api_to_update_config)

graph.add_edge(START, "ask")
graph.add_edge("ask", "route")
graph.add_edge("preview", "route")

graph.add_conditional_edges(
    "route",
    get_next_node,
    {
        "ask": "ask",
        "route": "route",
        "preview": "preview",
        "submit": "create_target_branch",
        END: END
    }
)

# Submit Chain
graph.add_edge("create_target_branch", "create_on_boarding_branch")
graph.add_edge("create_on_boarding_branch", "fetch_sorCodes")
graph.add_edge("fetch_sorCodes", "update_sor_codes_yaml")
graph.add_edge("update_sor_codes_yaml", "update_sor_codes_file")

graph.add_edge("update_sor_codes_file", "fetch_rules")
graph.add_edge("fetch_rules", "update_rules_yaml")
graph.add_edge("update_rules_yaml", "update_rules_file")

graph.add_edge("update_rules_file", "create_pr")
graph.add_edge("create_pr", "call_api_to_update_config")

graph.add_edge("call_api_to_update_config", END)

# --- Run ---
if __name__ == "__main__":
    app = graph.compile()
