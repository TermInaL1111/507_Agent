from pydantic import BaseModel
from typing import List, Tuple, Optional


class QueryRequest(BaseModel):
    session_id: Optional[str] = None
    query: str


class RAGRequest(BaseModel):
    query: str
    kb_type: Optional[str] = None


class SourceInfo(BaseModel):
    source_id: str
    file_id: Optional[str] = None
    doc_name: str
    kb_type: Optional[str] = None
    category: Optional[str] = None
    page: Optional[int] = None
    snippet: Optional[str] = None
    downloadable: bool = False


class SessionResponse(BaseModel):
    session_id: str
    history: List[Tuple[str, str]]


class AgentStep(BaseModel):
    thought: Optional[str] = None
    tool: Optional[str] = None
    tool_input: Optional[dict] = None
    tool_output: Optional[str] = None


class AgentResponse(BaseModel):
    response: str
    session_id: str
    steps: Optional[List[AgentStep]] = None


class RAGResponse(BaseModel):
    response: str
    answer: Optional[str] = None
    sources: List[SourceInfo] = []


class ReorderRequest(BaseModel):
    query: str
    documents: List[str]


class ReorderResponse(BaseModel):
    documents: List[dict]


class ScheduleEventBase(BaseModel):
    title: str
    type: str = "task"
    date: str = ""
    weekday: str
    startTime: str
    endTime: str
    location: str = ""
    teacher: str = ""
    repeat: str = "weekly"
    source: str = "manual"
    remark: str = ""


class ScheduleEventCreate(ScheduleEventBase):
    pass


class ScheduleEventResponse(ScheduleEventBase):
    id: int


class ScheduleConflictResponse(BaseModel):
    hasConflict: bool
    conflicts: List[ScheduleEventResponse] = []


class CampusLocationResponse(BaseModel):
    id: str
    name: str
    aliases: List[str] = []
    type: str
    latitude: float
    longitude: float
    description: str = ""
    address: str = ""
    tags: List[str] = []
    mapUrl: Optional[str] = None
