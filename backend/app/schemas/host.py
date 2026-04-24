from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Optional, List, Dict
from datetime import datetime


class HostGroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class HostGroupCreate(HostGroupBase):
    pass


class HostGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class HostGroupResponse(HostGroupBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class CredentialBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(password|ssh_key)$")
    username: Optional[str] = None
    password: Optional[str] = None
    private_key: Optional[str] = None
    passphrase: Optional[str] = None


class CredentialCreate(CredentialBase):
    pass


class CredentialUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    private_key: Optional[str] = None
    passphrase: Optional[str] = None


class CredentialResponse(BaseModel):
    id: str
    name: str
    type: str
    username: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CredentialDetailResponse(BaseModel):
    id: str
    name: str
    type: str
    username: Optional[str] = None
    created_at: datetime
    hosts_count: int = 0

    class Config:
        from_attributes = True


class HostBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    ip_address: str = Field(...)
    port: int = Field(default=22, ge=1, le=65535)
    host_type: str = Field(default="server", pattern="^(server|service)$")
    service_name: Optional[str] = None
    description: Optional[str] = None
    group_id: Optional[str] = None
    credential_id: Optional[str] = None
    variables: Dict = {}
    tags: List[str] = []


class HostCreate(HostBase):
    pass


class HostUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    host_type: Optional[str] = None
    service_name: Optional[str] = None
    description: Optional[str] = None
    group_id: Optional[str] = None
    credential_id: Optional[str] = None
    variables: Optional[Dict] = None
    tags: Optional[List[str]] = None


class HostResponse(HostBase):
    id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    group: Optional[HostGroupResponse] = None

    class Config:
        from_attributes = True


class HostConnectionTest(BaseModel):
    success: bool
    message: str
    response_time: Optional[float] = None
