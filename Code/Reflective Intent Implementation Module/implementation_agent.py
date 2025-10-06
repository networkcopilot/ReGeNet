import asyncio
import re
import os
import aiofiles
import shutil
import uuid

import json

from typing import  Callable, List, AsyncIterator
from message_protocol import(
    ImplementationTask,
    ImplementationResult,
    ImplementationReviewTask,
    ImplementationReviewResult,
    Reset,
)
from openai import AsyncAssistantEventHandler, AsyncClient
from typing import Dict, List
from openai.types.beta import AssistantStreamEvent
from autogen_core import  MessageContext, RoutedAgent, TopicId, default_subscription, message_handler
from global_variables import GlobalVariables

@default_subscription
class ImplementationAgent(RoutedAgent):
    """An agent for implementing user intents """


    def __init__(
        self,
        description: str,
        client: AsyncClient,
        assistant_id: str,
        thread_id: str,
        assistant_event_handler_factory: Callable[[], AsyncAssistantEventHandler], # simply overrides on text delta functionality to print the result to the screen.
    ) -> None:
        super().__init__(description)
        self._client = client
        self._assistant_id = assistant_id
        self._thread_id = thread_id
        self._assistant_event_handler_factory = assistant_event_handler_factory # the name of event handler mentioned above in line 35
        self._session_memory: Dict[str, List[ImplementationTask | ImplementationReviewTask | ImplementationReviewResult]] = {}


    @message_handler
    async def handle_Implementation_task(self, message: ImplementationTask, ctx: MessageContext) -> None:
        """Handle a message with files in it. This method adds the message to the thread and publishes a response."""
        
        global_var = GlobalVariables() # get the global variables instance
        global_var.start_timer() # start the timer for the implementation process
        # Store the messages in a temporary memory for this request only.
        session_id = str(uuid.uuid4())
        self._session_memory.setdefault(session_id, []).append(message)
        
        

        # -----------------------------files handling -----------------------------
        attachments_for_implementor= []
        
        global_var.clear_attachments_for_verifier() # make sure the variable is empty before we start a new run and adding files to it.
        global_var.set_iteration(1)
        output_dir_path = global_var.current_run_dir_path()
        # make sure the directory for the implementation results exists + all itterations file directory
        os.makedirs(f"{output_dir_path}/iteration_{global_var.get_iteration()}/assistant_files", exist_ok=True)
        os.makedirs(f"{output_dir_path}/All_assistant_files", exist_ok=True)
        for attachment in message.attachments:
            async with aiofiles.open(attachment, mode="rb") as file:
                file_content = await ctx.cancellation_token.link_future(asyncio.ensure_future(file.read())) #wait for the file to be read fully
            file_name = os.path.basename(attachment) # get the file name from the path
            # Upload the file as oai file (OpenAI file).
            oai_file = await ctx.cancellation_token.link_future(
                asyncio.ensure_future(self._client.files.create(file=(file_name, file_content), purpose="assistants"))
            )# OpenAI file with the purpose of "assistants" is used to upload files for the assistant to use.
            attachments_for_implementor.append({"file_id": oai_file.id, "tools": [{"type": "file_search"}]})
            # Save the message to the thread.
        prompt = f"""{message.content}
        The given intent:
        '{message.intent}'
        """
        await ctx.cancellation_token.link_future(
            asyncio.ensure_future(
                self._client.beta.threads.messages.create(
                    thread_id=self._thread_id,
                    content=prompt,
                    role="user",
                    attachments = attachments_for_implementor,
                    metadata={"sender": message.source},
                )
            )
        )

        #-------------------------------------------------------------------------
        # Generate a response.
        run_stream = await self._client.beta.threads.runs.create(
            thread_id=self._thread_id,
            assistant_id=self._assistant_id,
            stream=True # other option is false for polling, but we want to stream the response into the screen
        )
        await self.handle_run_stream(self._thread_id, run_stream)
        
        # Get all of the assistant's last message.
        messages = await ctx.cancellation_token.link_future(
            asyncio.ensure_future(self._client.beta.threads.messages.list(self._thread_id, order="asc"))
        ) # <----------------------NOTICE! this list of messages is in ascending order and not the default descending!!!

        last_user_message_index = None
        for index, assistant_message in enumerate(messages.data):
            if assistant_message.role == "user":
                last_user_message_index = index
        all_last_assistants_messages = messages.data[last_user_message_index+1:]

        # get the assistant's output
        implementation_text = ""
        for assistant_message in all_last_assistants_messages:
            implementation_text += assistant_message.content[0].text.value
            implementation_text +="\n"

        # call the verifier
        implementation_review_task = ImplementationReviewTask(session_id=session_id, intent=message.intent, implementation=implementation_text, original_attachments=message.attachments, updated_attachments=global_var.get_attachments_for_verifier())
        self._session_memory.setdefault(session_id, []).append(implementation_review_task)

        await self.publish_message(implementation_review_task, topic_id=TopicId("default", self.id.key))


    @message_handler
    async def handle_implementation_review_result(self, message: ImplementationReviewResult, ctx: MessageContext) -> None:
        
        # Store the verification result in the session memory.
        self._session_memory[message.session_id].append(message)
        # Obtain the files from previous messages.
        verification_request = next(
            m for m in reversed(self._session_memory[message.session_id]) if isinstance(m, ImplementationReviewTask)
        )
        assert verification_request is not None
        
        global_var = GlobalVariables() # get the global variables instance
        global_var.clear_attachments_for_verifier() #cleaning the variable files value
        global_var.increment_iteration() # increment the iteration number for the next conversation iteration
        output_dir_path = global_var.current_run_dir_path()
        # make sure the directory for the implementation results for this iteration exists
        os.makedirs(f"{output_dir_path}/iteration_{global_var.get_iteration()}/assistant_files", exist_ok=True)
        
        # call implementation assistant with the verification result:
        await ctx.cancellation_token.link_future(
            asyncio.ensure_future(
                self._client.beta.threads.messages.create(
                    thread_id=self._thread_id,
                    content=f"Verifier response:\n{message.review}\n\n The given intent: \n{message.intent}",
                    role="user",
                    metadata={"sender": "Verifier Assistant"},
                )
            )
        )
        run_stream = await self._client.beta.threads.runs.create(
            thread_id=self._thread_id,
            assistant_id=self._assistant_id,
            stream=True
        )
        await self.handle_run_stream(self._thread_id, run_stream)
            
        # Get the last messages from the implementation assistant
        messages = await ctx.cancellation_token.link_future(
            asyncio.ensure_future(self._client.beta.threads.messages.list(self._thread_id, order="asc"))
        )# <----------------------NOTICE! this list of messages is in ascending order and not the default descending!!!
        
        # Check if the implementation was approved by the verifier:
        if message.approved:
            global_var.end_timer() # end the timer for the implementation process
            os.makedirs(f"{output_dir_path}/final_results", exist_ok=True)
            # remove the iteration folder and its sub directory, since this the itteration before was the final iteration
            if os.path.exists(f"{output_dir_path}/iteration_{global_var.get_iteration()}/assistant_files"):
                os.rmdir(f"{output_dir_path}/iteration_{global_var.get_iteration()}/assistant_files")
                os.rmdir(f"{output_dir_path}/iteration_{global_var.get_iteration()}")
            global_var.set_iteration(global_var.get_iteration() - 1) # decrement the iteration number since we are done with this iteration
            
            last_message = messages.data[-1]
            result = last_message.content[0].text.value
            try:
                parsed_result = json.loads(result)
            except json.decoder.JSONDecodeError:
                sub_result = re.sub(r"^```json\s*\n?", "", result)
                sub_result = re.sub(r"\n?```$", "", sub_result)
                parsed_result = json.loads(sub_result)
            
            try:
                await self.publish_message(
                    ImplementationResult(
                        content=parsed_result["implementation_explanation"],
                        attachments=parsed_result["updated_attachments"],
                        review=message.review,
                    ),
                    topic_id=TopicId("default", self.id.key),
                )
                print("Implementation Result:")
                print("-" * 80)
                print(f"Attachments:\n {parsed_result['updated_attachments']}")
                print("-" * 80)
                print(f"Implementation Explenation:\n{parsed_result['implementation_explanation']}")
                print("-" * 80)
                print(f"Review:\n{message.review}")
                print("-" * 80)
                
                # copy the updated files to the final results folder
                for attachment in parsed_result["updated_attachments"]:
                    # src = f"scenarios_results/{global_variables.scenario}/assistant_files/{attachment}"
                    src = f"{output_dir_path}/iteration_{global_var.get_iteration()}/assistant_files/{attachment}"
                    # dst = f"scenarios_results/{global_variables.scenario}/final_results/{attachment}"
                    dst = f"{output_dir_path}/final_results/{attachment}"
                    shutil.copyfile(src, dst)
                    
                async with aiofiles.open(f"{output_dir_path}/Full_Conversation.txt", mode="a", encoding="utf-8") as f:
                    for conversation_message in messages.data[:-1]:
                        await f.write(f"{conversation_message.role}:\n {conversation_message.content[0].text.value}\n")
                        await f.write("-" * 80)
                        await f.write("\n")
                    await f.write(f"assistant:\n {parsed_result['implementation_explanation']}\n")
                    await f.write(f"Updated files:\n {parsed_result['updated_attachments']}\n")
                    
            except KeyError:
                print(f"Couldn't find the keys in the JSON result, the resulted JSON is:\n{parsed_result}\n\n")
                
            
            
        else:
            last_user_message_index = None
            for index, assistant_message in enumerate(messages.data):
                if assistant_message.role == "user":
                    last_user_message_index = index
            all_last_assistants_messages = messages.data[last_user_message_index+1:]


            # get the assistant's output
            implementation_text = ""
            for assistant_message in all_last_assistants_messages:
                implementation_text += assistant_message.content[0].text.value
                implementation_text +="\n"
            
            #create output file of this iteration
            async with aiofiles.open(f"{output_dir_path}/iteration_{(global_var.get_iteration()-1)}/Full_Conversation.txt", mode="a", encoding="utf-8") as f:
                    for conversation_message in messages.data[:-1]:
                        await f.write(f"{conversation_message.role}:\n {conversation_message.content[0].text.value}\n")
                        await f.write("-" * 80)
                        await f.write("\n")
                        
            # call the verifier
            # verification_request.original_attachments include the original files from the user
            # attachments_for_verifier include the updated files for verification
            implementation_review_task = ImplementationReviewTask(session_id=message.session_id, intent= message.intent, implementation=implementation_text, original_attachments=verification_request.original_attachments, updated_attachments=global_var.get_attachments_for_verifier())
            self._session_memory.setdefault(message.session_id, []).append(implementation_review_task)

            await self.publish_message(implementation_review_task, topic_id=TopicId("default", self.id.key))




#-------------------------------------- Instead of EventHandler class: --------------------------------------
    async def handle_run_stream(self, thread_id: str, run_stream: AsyncIterator[AssistantStreamEvent]):
        global_var = GlobalVariables() # get the global variables instance
        output_dir_path = global_var.current_run_dir_path()
        async for event in run_stream:
            ev = event.event  # e.g. 'thread.run.requires_action' or 'thread.message.completed'
            data = event.data
            if ev == "thread.run.requires_action":
                # here you'd call your function/tool, then submit the outputs...
                tool_outputs = []
                
                for tool in data.required_action.submit_tool_outputs.tool_calls:
                    if tool.function.name == "create_file":
                        args = json.loads(tool.function.arguments)

                        new_file_path = f"{output_dir_path}/iteration_{global_var.get_iteration()}/assistant_files/{args['file_name']}"
                        async with aiofiles.open(new_file_path, mode="w", encoding="utf-8") as f:
                            await f.write(args['content'])
                        # Make a copy of the new file in the all iterations directory
                        all_files_dir_file_path = f"{output_dir_path}/All_assistant_files/{args['file_name']}"
                        shutil.copyfile(new_file_path, all_files_dir_file_path)
                        global_var.add_attachment_for_verifier(new_file_path)
                        tool_outputs.append({"tool_call_id": tool.id, "output": args['file_name']})
                
                # send the tool output back into the run and continue streaming
                next_stream = await self._client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=data.id,
                    tool_outputs= tool_outputs,
                    stream = True,
                )
                # recurse into the new stream
                await self.handle_run_stream(thread_id, next_stream)
            elif ev =="thread.message.delta":
                for content_delta in event.data.delta.content or []:
                    if content_delta.type == "text" and content_delta.text and content_delta.text.value:
                        print(content_delta.text.value, end="", flush=True)
            elif ev == "thread.run.completed":
                # Handle the completion of the run
                return


