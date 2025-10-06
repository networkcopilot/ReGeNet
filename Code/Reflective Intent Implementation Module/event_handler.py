from openai import AsyncAssistantEventHandler, AsyncClient
from openai.types.beta.threads import Message, Text, TextDelta
from openai.types.beta.threads.runs import RunStep, RunStepDelta
from openai.types.beta import AssistantStreamEvent
from typing_extensions import override
import json
import aiofiles
import asyncio
import global_variables
import os

api_key = os.getenv("OPENAI_API_KEY")

class EventHandler(AsyncAssistantEventHandler):


    @override
    async def on_text_delta(self, delta: TextDelta, snapshot: Text) -> None:
        print(delta.value, end="", flush=True)

    # override
    # async def on_event(self, event: AssistantStreamEvent) -> None:
    #     if event.event == 'thread.run.requires_action':
    #         run_id = event.data.id  # Retrieve the run ID from the event data
    #         await self.handle_requires_action(event.data, run_id)


    # async def handle_requires_action(self, data, run_id)-> None:
    #     tool_outputs = []
    #     for tool in data.required_action.submit_tool_outputs.tool_calls:
    #         if tool.function.name == "create_file":
    #             args = json.loads(tool.function.arguments)
    #             async with aiofiles.open(f"assistant_files/{args['file_name']}", mode="w") as f:
    #                 await f.write(args['content'])
    #         updated_files.attachments_for_verifier.append(f"assistant_files/{args['file_name']}")
    #         tool_outputs.append({"tool_call_id": tool.id, "output": args['file_name']})
    #     client=AsyncClient(api_key=api_key)
    #     asyncio.ensure_future(client.beta.threads.runs.submit_tool_outputs(
    #         thread_id=self.current_run.thread_id,
    #         run_id=run_id,
    #         tool_outputs=tool_outputs,
    #         )
    #     )
        # await self.submit_tool_outputs(tool_outputs, run_id)

    # async def submit_tool_outputs(self, tool_outputs, run_id)-> None:
    #     client=AsyncClient(api_key=api_key)
    #     await client.beta.threads.runs.submit_tool_outputs(
    #         thread_id=self.current_run.thread_id,
    #         run_id=run_id,
    #         tool_outputs=tool_outputs,
    #     )