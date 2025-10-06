
from openai import OpenAI, AsyncClient
import asyncio
import logging
from autogen_core import DefaultTopicId, SingleThreadedAgentRuntime, AgentId
from implementation_agent import ImplementationAgent
from verifier_agent import VerifierAgent
from event_handler import EventHandler
import pandas as pd
#from function_event_handler import FunctionEventHandler
from message_protocol import ImplementationTask
from create_assistants import verifier_assistant_creation, implementation_assistant_creation
import os
from global_variables import GlobalVariables
from dotenv import load_dotenv, set_key, find_dotenv

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# -------------------------------logging --------------------------------
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("phase4_log.log"),
        # logging.StreamHandler()
    ])
logging.getLogger("autogen_core").setLevel(logging.WARN)

# in case you have modified the assistants instructions, set this to True:
assistant_instructions_modified = False
global_var = GlobalVariables()
#@TODO: change before running experiment
#run variable
run_number = global_var.get_run_number() # 1
model = "gpt-4.1-mini" #modify as needed
global_var.set_model(model)
platforms = ["GNS3"]#,"Paper_Sketches","PowerPoint"]
diagram_types = ["Normal"]#,"Messy_Layout", "No_Labels_On_Edges"]
scenarios =  ["IP_Traffic_Export"]#["Adding_Communication_Servers", "Adding_DMZ", "Adding_DRA", "Adding_Local_PCs", "Internet_Connectivity", "Role_Based_CLI_Access", "Time_Based_Access_List", "Transparent_IOS_Firewall", "Basic_Zone_Based_Firewall", "IP_Traffic_Export"]


async def main_run():

    # on assistant instruction modification:
    load_dotenv()
    model = global_var.get_model()
    if assistant_instructions_modified:
        # oai_verifier_assistant = verifier_assistant_creation(api_key)
        oai_verifier_assistant = verifier_assistant_creation(api_key, model)
        # oai_implementation_assistant = implementation_assistant_creation(api_key)
        oai_implementation_assistant = implementation_assistant_creation(api_key,model)
        env_path = find_dotenv(".env_public")
        set_key(env_path, "VERIFIER_ASSISTANT_ID", oai_verifier_assistant.id)
        set_key(env_path, "IMPLEMENTATION_ASSISTANT_ID", oai_implementation_assistant.id)
        env_path = find_dotenv(".env")
        set_key(env_path, "VERIFIER_ASSISTANT_ID", oai_verifier_assistant.id)
        set_key(env_path, "IMPLEMENTATION_ASSISTANT_ID", oai_implementation_assistant.id)
    
    
    verifier_assistant_id = os.getenv("VERIFIER_ASSISTANT_ID", None)
    implementation_assistant_id = os.getenv("IMPLEMENTATION_ASSISTANT_ID", None)

    # vision_output_dir = f"/Vision_Results/{model}"
    output_folder = f"Implementation_results/{model}"

    # ---- Time evaluation file creation and reading----
    run_number = global_var.get_run_number()
    implementation_time_calc_file_address = f"Implementation_results/{model}/Implementation_time_run{run_number}.csv"
    if os.path.isfile(implementation_time_calc_file_address):
        phase4_df = pd.read_csv(implementation_time_calc_file_address)
    else:
        phase4_df = pd.DataFrame(
            columns=["Scenario", "Platform", "Diagram_Type", "Run", "Model", "Time", "Cost",
                    "Reasoning_Text", "Prompt_tokens", "Completion_tokens", "Error_message"])
    os.makedirs(output_folder, exist_ok=True)


    #running on platforms, diagram types and scenarios
    for platform in platforms:
        global_var.set_platform(platform)

        for diagram_type in diagram_types:
            global_var.set_diagram_type(diagram_type)

            for scenario in scenarios:

                global_var.set_scenario(scenario)
                global_var.set_run_number(run_number)
                # @TODO: make sure all dirs that implementer and verifier write to are updated
                # os.makedirs(f"scenarios_results/{scenario_name}/assistant_files", exist_ok=True)
                # os.makedirs(f"scenarios_results/{scenario_name}/final_results", exist_ok=True)
                # os.makedirs(f"scenarios_results/{scenario_name}/assistant_files", exist_ok=True)
                # os.makedirs(f"scenarios_results/{scenario_name}/final_results", exist_ok=True)
                try:
                    result = await phase4_run(scenario, platform, diagram_type, model, run_number, verifier_assistant_id, implementation_assistant_id)
                    logging.info("Completed run for scenario: %s, platform: %s, diagram type: %s, model: %s", scenario, platform, diagram_type, model)
                    verifier_thread_id = global_var.get_verifier_thread_id()
                    implementation_thread_id = global_var.get_implementation_thread_id()
                    verifier_runs = client.beta.threads.runs.list(verifier_thread_id)
                    implementor_runs = client.beta.threads.runs.list(implementation_thread_id)
                    
                    full_usage = {"prompt_tokens": 0, "completion_tokens": 0}
                    for run in verifier_runs.data + implementor_runs.data:
                        full_usage["prompt_tokens"] += run.usage.prompt_tokens
                        full_usage["completion_tokens"] += run.usage.completion_tokens
                    cost = (full_usage["prompt_tokens"]/ 1000000)*0.4 + (full_usage["completion_tokens"]/ 1000000)*1.6 # cost for gpt-4.1-mini 
                        
                    new_row = {"Scenario":scenario, "Platform":platform, "Diagram_Type":diagram_type, "Run": run_number, "Model":model, "Time":global_var.get_elapsed_time(), "Cost":cost,
                        "Reasoning_Text": None,"Prompt_tokens":full_usage["prompt_tokens"], "Completion_tokens":full_usage["completion_tokens"] , "Error_message":None}
                    phase4_df.loc[len(phase4_df)] = new_row
                    phase4_df.to_csv(implementation_time_calc_file_address, index=False)
                except Exception as e:
                    logging.error(e)
                    new_row ={"Scenario":scenario, "Platform":platform, "Diagram_Type":diagram_type, "Run": run_number, "Model":model, "Time":None, "Cost":None,
                        "Reasoning_Text": None,"Prompt_tokens":None, "Completion_tokens":None, "Error_message":str(e)}
                    phase4_df.loc[len(phase4_df)] = new_row
                    phase4_df.to_csv(implementation_time_calc_file_address, index=False)
                    



async def phase4_run(scenario_name: str, platform:str, diagram_type:str, model:str,run:int, verifier_assistant_id: str, implementation_assistant_id: str):
    # -------------------------------Verifier assistant-------------------------------
    oai_verifier_assistant = client.beta.assistants.retrieve(verifier_assistant_id)
    # Create a vector store to be used for file search.
    verifier_assistant_vector_store = client.vector_stores.create()
    # Create a thread which is used as the memory for the assistant.
    verifier_thread = client.beta.threads.create(
        tool_resources={"file_search": {"vector_store_ids": [verifier_assistant_vector_store.id]}},)
    global_var.set_verifier_thread_id(verifier_thread.id)
    # -------------------------------Implementation assistant-------------------------------
    oai_implementation_assistant = client.beta.assistants.retrieve(implementation_assistant_id)
    #oai_implementation_assistant = implementation_assistant_creation(api_key)
    # Create a vector store to be used for file search.
    implementation_assistant_vector_store = client.vector_stores.create()
    # Create a thread which is used as the memory for the assistant.
    implementation_thread = client.beta.threads.create(
        tool_resources={"file_search": {"vector_store_ids": [implementation_assistant_vector_store.id]}},)
    global_var.set_implementation_thread_id(implementation_thread.id)
    # -------------------------------Agent Runtime-------------------------------
    runtime = SingleThreadedAgentRuntime()
    # function_event_handler = FunctionEventHandler(client=client, thread_id=implementation_thread.id)
    
    await ImplementationAgent.register(
        runtime,
        "implementation_assistant",
        lambda: ImplementationAgent(
            description="OpenAI Networking Intent Implementation Assistant Agent",
            client=AsyncClient(api_key=api_key),
            assistant_id=oai_implementation_assistant.id,
            thread_id=implementation_thread.id,
            assistant_event_handler_factory=lambda: EventHandler(),
        ),)

    await VerifierAgent.register(
        runtime,
        "verifier_assistant",
        lambda: VerifierAgent(
            description="OpenAI Networking Intent Implementation Verifier Assistant Agent",
            client=AsyncClient(api_key=api_key),
            assistant_id=oai_verifier_assistant.id,
            thread_id=verifier_thread.id,
            assistant_event_handler_factory=lambda: EventHandler(),
        ),
    )


    verifier_agent = AgentId("verifier_assistant", "default")
    implementation_agent = AgentId("implementation_assistant", "default")
    
    try:
        runtime.start()
        content = f"""Hello network architecture expert, Here you were given two text files: a full configuration file named “Total_Configs.txt” and a textual representation of the topology named “Original_Topology.txt”. Please ensure that you read both of the provided files entirely and make the necessary modifications according to the user's intent, apply the modifications without waiting for confirmation for your actions."""
        #@TODO: rerun gt topology ablation with correct topology ground truth files
        # topology_file = f"scenarios_initial_files/{scenario_name}/Original_Topology.json"
        topology_file = f"Vision_results/{model}/{platform}/{diagram_type}/{scenario_name}/Topology(Run{run}).json"
        #@TODO: make sure this are the appropriate files (configs)
        config_file = f"scenarios_initial_files/{scenario_name}/Total_Configs.txt"
        file_attachments = [topology_file, config_file]
        #@TODO: consider updating some of the intents or adress the differences (declerative vs percise descriptions) [Basic z-ne-based firewall,IP traffic export, transparent IOS, Role Based]
        intent = open(f"scenarios_initial_files/{scenario_name}/intent.txt", mode='r', encoding="utf8").read()
        await runtime.publish_message(
            message = ImplementationTask(content=content, intent=intent, attachments = file_attachments, source="user"),
            topic_id=DefaultTopicId(),
            )
        await runtime.stop_when_idle()
        await runtime.close()
        return f"Run completed for scenario {scenario_name} on platform {platform} with diagram type {diagram_type} with model:{model}."
    except Exception as e:
        await runtime.close()
        raise Exception(f"An error occurred during the run for scenario {scenario_name} on platform {platform} with diagram type {diagram_type} with model {model}: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main_run())