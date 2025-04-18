from pydantic import BaseModel
from typing import Optional, List, Dict, Any


# Pydantic models for request/response
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

class SessionState(BaseModel):
    messages: List[Dict[str, Any]] = []