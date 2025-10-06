from dataclasses import dataclass


@dataclass
class ImplementationTask:
    content: str # aka user prompt (not the intent)
    intent: str # the text from the intent file
    attachments: list[str] # list of file paths
    source:str # "verifier" or "user" -> the sender of the message

@dataclass
class ImplementationResult:
    content: str # the content of the implementation assistant's response with the summary of its work across the session
    attachments: list[str] # list of only the final updated file paths
    review: str # the last review of the verifier assistant


@dataclass
class ImplementationReviewTask:
    session_id: str # the session id of the implementation task
    intent: str # the intent text
    implementation: str # the last message of the implementation assistant
    original_attachments: list[str] # the original attachments for the implementation task
    updated_attachments: list[str] # the updated attachments the implementation assistant has created

@dataclass
class ImplementationReviewResult:
    session_id: str # same as in ImplementationReviewTask
    intent: str
    review: str # the review of the implementation assistant by the verifier assistant
    approved: bool # whether the implementation is approved or not
    

@dataclass
class Reset:
    pass