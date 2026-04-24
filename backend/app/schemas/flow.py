from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Any
from datetime import datetime


class FlowBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tags: List[str] = []


class FlowCreate(FlowBase):
    flow_data: Dict = {}


class FlowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class FlowDesignUpdate(BaseModel):
    name: Optional[str] = None
    flow_data: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None


class FlowResponse(FlowBase):
    id: str
    status: str
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FlowDetailResponse(FlowResponse):
    flow_data: Dict = {}
    variables: Dict = {}


class FlowExecutionCreate(BaseModel):
    host_ids: Optional[List[str]] = None  # 指定执行主机
    variables: Optional[Dict[str, Any]] = None  # 额外变量


class FlowExecutionResponse(BaseModel):
    id: str
    flow_id: str
    flow_name: Optional[str] = None  # 流程名称
    user_id: Optional[str] = None
    status: str
    trigger_type: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result_summary: Dict = {}
    created_at: datetime

    class Config:
        from_attributes = True


class NodeExecutionResponse(BaseModel):
    id: str
    execution_id: str
    node_id: str
    node_name: Optional[str] = None
    node_type: Optional[str] = None
    host_id: Optional[str] = None
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlaybookTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    content: str
    category: Optional[str] = None
    variables_schema: Dict = {}
    tags: List[str] = []


class PlaybookTemplateCreate(PlaybookTemplateBase):
    pass


class PlaybookTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    variables_schema: Optional[Dict] = None
    tags: Optional[List[str]] = None


class PlaybookTemplateResponse(PlaybookTemplateBase):
    id: str
    is_public: bool
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ScriptTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    script_type: str = Field(..., pattern="^(shell|python|powershell)$")
    content: str
    category: Optional[str] = None
    tags: List[str] = []


class ScriptTemplateCreate(ScriptTemplateBase):
    pass


class ScriptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    script_type: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class ScriptTemplateResponse(ScriptTemplateBase):
    id: str
    is_public: bool
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ScheduledJobBase(BaseModel):
    name: str
    cron_expression: str
    description: Optional[str] = None


class ScheduledJobCreate(ScheduledJobBase):
    flow_id: str


class ScheduledJobUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class ScheduledJobResponse(ScheduledJobBase):
    id: str
    flow_id: str
    flow_name: Optional[str] = None
    enabled: bool
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
