from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class FriendAddRequest(BaseModel):
    friend_username: str


class GroupCreate(BaseModel):
    name: str
    member_ids: list[int] = []


class GroupOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class PrivateMessageCreate(BaseModel):
    receiver_id: int
    content: str | None = None
    image_url: str | None = None


class GroupMessageCreate(BaseModel):
    group_id: int
    content: str | None = None
    image_url: str | None = None


class MessageOut(BaseModel):
    id: int
    sender_id: int
    receiver_id: int | None
    group_id: int | None
    content: str | None
    image_url: str | None
    is_group_message: bool
    created_at: datetime

    class Config:
        from_attributes = True
