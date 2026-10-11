from pydantic import BaseModel


class AgentEventOut(BaseModel):
    id: int
    session_id: str
    step: str
    message: str
    status: str
    timestamp: str
