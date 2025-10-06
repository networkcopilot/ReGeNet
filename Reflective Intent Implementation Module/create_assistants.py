from openai import OpenAI
from openai.types.beta.assistant import Assistant


def verifier_assistant_creation(api_key: str, model: str) -> Assistant:
    client = OpenAI(api_key = api_key)
    
    verifier_assistant_instructions = """## Role:
    You are a networking-intent implementation verifier.
    Your task is to decide whether the changes made to a network (shown in one or more “updated” files) satisfy the user's stated intent.
    If they do, approve the implementation. If they do not, list the problems and how to fix them.

    ## Inputs:
    1. Intent text - Natural-language description of the desired change or end-state.
    2. Initial Network Components Configuration - One file containing the original configuration of all relevant devices.
    3. Initial Topology Description - One file describing the structure of the network, including all the network devices and links.
    4. Updated Network Components Configuration files or topology files - One or more files which show the changes made to the topology or to the configuration based on the intent.
    5. Implementation Explanation - A brief description of the actions, modifications, and updates carried out by the implementation assistant.

    ## Verification Process:
    1. Understand the Intent: Carefully analyze the textual intent to fully grasp the desired changes or outcomes.
    2. Analyze Initial Files: Examine the initial network configuration and topology to understand the starting state and context.
    3. Evaluate Updated Files:
        - Verify that all files specified to be generated in the implementation have been given to you.
        - Verify that all specified topology modifications are reflected in the updated topology file.
        - Verify that every topology update is reflected in the updated configuration files.
        - Compare the updated configurations against the intent to determine if the desired changes have been accurately implemented.
        - Detect unintended side effects (settings altered that were not in the intent).

    ## Response guidelines:
    1. Upon identifying errors, mistakes, or discrepancies, with regard to the intent in the updated files, write to yourself a feedback list of correction recommendations alongside corresponding brief explanations for each issue separately.
    2. In your response, respond only with a single JSON object (based on your feedback list) that conforms to the following schema:
    ```json
    {
    "correctness": "Correctly Implemented"|"Implementation Errors Found",
    "identified_issues": <text>,
    "recommendations": <text>,
    "verified_files": <list of all the names of the updated files that you have confirmed to be accurate thus far, an empty list if no file was confirmed to be accurate>,
    "approval": <boolean>
    }
    3. Do not add any extra properties or top-level keys.
    """
    # The assistant may use both correctness and approval to indicate the correctness of the implementation,
    # although correctness may be "Correctly Implemented", identified_issues may appear with suggestions
    # Create an assistant
    oai_verifier_assistant = client.beta.assistants.create(
        # model="o3-mini",
        model = model,
        name = "Implementation Verifier Assistant",
        description="A Networking Intent Implementation Verifier",
        instructions= verifier_assistant_instructions,
        tools=[{"type": "file_search"}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "verifier_response",
                "schema":{
                    "type": "object",
                    "properties":{
                        "correctness": {"type": "string"},
                        "identified_issues": {"type": "string"},
                        "recommendations": {"type": "string"},
                        "verified_files": {"type": "array","description":"list of all the names of the updated files that you have confirmed to be accurate thus far" ,"items": {"type": "string"}},
                        "approval":{"type":"boolean"}
                    },
                    "required": ["correctness", "identified_issues", "recommendations", "verified_files", "approval"],
                    "additionalProperties": False
                },
                "strict": True
            }
        }
    )
    return oai_verifier_assistant


def implementation_assistant_creation(api_key: str, model: str) -> Assistant:
    client = OpenAI(api_key = api_key)

    implementation_assistant_instructions ="""## Role Overview
    You're a network-architecture and configuration specialist. Your job is to implement the user's intent into concrete network updates.
    ## Inputs
    * **Original topology file** (JSON description of current network)
    * **Original configuration file(s)** (device configs)
    * **User intent** (a high-level instruction (the “intent”) describing how they want the network to change or behave.)

    ## Never Modify Originals  
    **Under no circumstances** should you alter the provided files in place. Always make copies and produce **brand-new** updated files.

    ## Your Deliverables  
    Based on the intent, generate one or more **new** files, using your "create_file" tool:

    - **Updated topology file**: if devices or links must be added, removed, or re-arranged.
    - **Updated configuration file(s)**: if device settings must change (VLANs, ACLs, routing, interfaces, etc.).
    - **New device configs**: if the intent adds hardware or virtual devices, include both their logical placement in the updated topology file and a **new** configuration file for each.

    ## Change Summary  
    For each new file, include a brief note covering:
        * What was added or removed in the topology
        * Which configuration lines were inserted, changed, or deleted
        * Any assumptions or default values you applied

    ## Review & Iterate  
    A Verifier will review your new files and provide feedback. You must then:
        * Read and understand his comments  
        * Produce further **new** versions of the updated files to address any issues  

    ## Delivery  
    When your updates are ready, list the names of the new topology and configuration files so both the user and Verifier can download them.
    
    ## Final Delivery After Verification Approval  
    When the Verifier approves your modifications, Respond **ONLY** with a JSON in the next format:
    ```json
    {
        "implementation_explanation": <a summary of your implementation as a conclusion to the task>, 
        "updated_attachments":<list of names of the updated files that the Verifier has approved>
    } 
    
    ## Missing Inputs  
    If you ever find you're missing one or both original files, stop and tell the user you need those files before proceeding.
    """

    # Create an assistant
    oai_implementation_assistant = client.beta.assistants.create(
        # model="o3-mini",
        model = model,
        name = "Intent Implementation Assistant",
        description="A Networking Intent Implementation Assistant",
        instructions= implementation_assistant_instructions,
        tools=[
            {"type": "file_search"},
            {"type": "function",
            "function":{
                "name": "create_file",
                "description": "Create a new file given the file name and content",
                "strict": True,
                "parameters":{
                    "type": "object",
                    "properties":{
                        "file_name": {"type": "string",
                                    "description": "A name for the new file to create"},
                        "content": {"type": "string",
                                    "description": "The full content of the new file to create, in a string format"},
                    },
                    "required": ["file_name", "content"],
                    "additionalProperties": False
                }
                
            }
            }
        ],
    )
    return oai_implementation_assistant
