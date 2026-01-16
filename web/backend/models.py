from pydantic import BaseModel


class LookupRequest(BaseModel):
    selection: str
    phrase: str | None = None
    paragraph: str | None = None
    file: str | None = None


class LookupResponse(BaseModel):
    type: str  # "translation" | "dictionary"
    query: str
    translation: str
    explanations: str
    context: dict | None = None


class ConversationRequest(BaseModel):
    question: str


class ConversationResponse(BaseModel):
    answer: str


class HistoryResponse(BaseModel):
    entries: list[dict]
