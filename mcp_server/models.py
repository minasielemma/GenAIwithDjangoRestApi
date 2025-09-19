from typing import Optional
from pydantic import BaseModel


class EmailRequest(BaseModel):
    email: Optional[str] = None
    provider: Optional[str] = None 
    model: Optional[str] = None   