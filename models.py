from pydantic import BaseModel, Field
from typing import Optional, List

class User(BaseModel):
    id: int
    name: str
    age: int
    gender: str
    phone_no: str
    pincode: str
    address: str

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str
    error: Optional[str] = None
