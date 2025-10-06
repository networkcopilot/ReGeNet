import asyncio
from typing import Any, Callable, List
from message_protocol import(
    ImplementationTask,
    ImplementationResult,
    ImplementationReviewTask,
    ImplementationReviewResult,
)
import os
import aiofiles
from openai import AsyncAssistantEventHandler, AsyncClient
import json
import shutil

from typing import Dict, List
from global_variables import GlobalVariables

from autogen_core import AgentId, MessageContext, RoutedAgent, TopicId, default_subscription, message_handler



@default_subscription
class VerifierAgent(RoutedAgent):
    """An agent for verifing the implementation assistants' result """


    def __init__(
        self,
        description: str,
        client: AsyncClient,
        assistant_id: str,
        thread_id: str,
        assistant_event_handler_factory: Callable[[], AsyncAssistantEventHandler],
    ) -> None:
        super().__init__(description)
        self._client = client
        self._assistant_id = assistant_id
        self._thread_id = thread_id
        self._assistant_event_handler_factory = assistant_event_handler_factory
        self._session_memory: Dict[str, List[ImplementationReviewTask | ImplementationReviewResult]] = {}


    @message_handler
    async def handle_implementation_review_task(self, message: ImplementationReviewTask, ctx: MessageContext) -> None:
        # Format the prompt for the verification review.
        # Gather the previous feedback if available.
        previous_feedback = ""
        if message.session_id in self._session_memory:
            previous_review = next(
                (m for m in reversed(self._session_memory[message.session_id]) if isinstance(m, ImplementationReviewResult)),
                None,
            )
            if previous_review is not None:
                previous_feedback = f"Previous feedback:\n{previous_review.review}\n"
        if not message.updated_attachments:
            raise ValueError("----------No updated attachments provided!!!!!-----------------")
        # Store the messages in a temporary memory for this request only.
        # notes for roobs: maybe we should add the previously updated files as well? answer for roobs: nope.
        original_attachments_basenames = [os.path.basename(attachment) for attachment in message.original_attachments]
        updated_attachments_basenames = [os.path.basename(attachment) for attachment in message.updated_attachments]
        
        self._session_memory.setdefault(message.session_id, []).append(message)
        
        prompt = f"""The problem statement is:\n{message.intent}.\n
        The answer of the Implementation Assistant is:\n
        '{message.implementation}'\n
        The original files before implementations are:\n
        {original_attachments_basenames}
        The updated files are:\n
        {updated_attachments_basenames}\n
        {previous_feedback}\n
        Please verify the correctness of the implementation and that the intent was fully implemented. If previous feedback was provided, see if it was addressed.
        """

        assistant_attachments = []
        all_attachments = message.original_attachments + message.updated_attachments
        for attachment in all_attachments:
            async with aiofiles.open(attachment, mode="rb") as file:
                file_content = await ctx.cancellation_token.link_future(asyncio.ensure_future(file.read()))
            file_name = os.path.basename(attachment)
            # Upload the file.
            oai_file = await ctx.cancellation_token.link_future(
                asyncio.ensure_future(self._client.files.create(file=(file_name, file_content), purpose="assistants"))
            )
            assistant_attachments.append({"file_id": oai_file.id, "tools": [{"type": "file_search"}]})

        await ctx.cancellation_token.link_future(
            asyncio.ensure_future(
                self._client.beta.threads.messages.create(
                    thread_id=self._thread_id,
                    content=prompt,
                    role="user",
                    attachments = assistant_attachments,
                    metadata={"sender": "Intent Implementation Assistant"},
                )
            )
        )
        # Generate a response.
        async with self._client.beta.threads.runs.stream(
            thread_id=self._thread_id,
            assistant_id=self._assistant_id,
            event_handler=self._assistant_event_handler_factory(),
        ) as stream:
            await ctx.cancellation_token.link_future(asyncio.ensure_future(stream.until_done()))

        # Get the last message.
        messages = await ctx.cancellation_token.link_future(
            asyncio.ensure_future(self._client.beta.threads.messages.list(self._thread_id, order="desc", limit=1))
        )
        last_message = messages.data[0].content[0].text.value
        # Parse the response JSON.
        # review_json:"correctness": {"type": "string"},
        #             "identified_issues": {"type": "string"},
        #             "recommendations": {"type": "string"},
        #             "verified_files": {"type": "array","description":"list of all the names of the updated files that you have confirmed to be accurate thus far" ,"items": {"type": "string"}},
        #             "approval":{"type":"boolean"}

        #         },
        review = json.loads(last_message)
        global_var = GlobalVariables() # get the global variables instance
        output_dir_path = global_var.current_run_dir_path()
        # if the approved file is from one of the previous iterations - add it to the current iteration directory
        if "verified_files" not in review:
            review["verified_files"] = []
        for approved_file in review["verified_files"]:
            if not os.path.exists(f"{output_dir_path}/iteration_{global_var.get_iteration()}/assistant_files/{approved_file}"):
                src = f"{output_dir_path}/All_assistant_files/{approved_file}"
                dst = f"{output_dir_path}/iteration_{global_var.get_iteration()}/assistant_files/{approved_file}"
                shutil.copyfile(src, dst)
        review_text = "\n".join([f"{k}:{v}" for k,v in review.items()])
        approved = review["approval"]
        implementation_review_result = ImplementationReviewResult(session_id=message.session_id, intent=message.intent, review=review_text, approved=approved)
        self._session_memory.setdefault(message.session_id, []).append(implementation_review_result)

        await self.publish_message(implementation_review_result, topic_id=TopicId("default", self.id.key))