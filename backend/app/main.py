import os
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket, WebSocketDisconnect
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from .auth import create_access_token, get_current_user, hash_password, verify_password
from .database import Base, engine, get_db
from .models import ChatGroup, Message, User, friendships
from .schemas import (
    FriendAddRequest,
    GroupCreate,
    GroupMessageCreate,
    GroupOut,
    MessageOut,
    PrivateMessageCreate,
    Token,
    UserCreate,
    UserOut,
)

Base.metadata.create_all(bind=engine)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Mini WeChat Clone")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        sockets = self.active_connections.get(user_id, [])
        if websocket in sockets:
            sockets.remove(websocket)
        if not sockets and user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_to_user(self, user_id: int, payload: dict):
        for ws in self.active_connections.get(user_id, []):
            await ws.send_json(payload)


manager = ConnectionManager()


@app.post("/auth/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    db_user = User(username=user.username, password_hash=hash_password(user.password))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/auth/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return Token(access_token=create_access_token(user.username))


@app.post("/friends/add", response_model=list[UserOut])
def add_friend(
    request: FriendAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend = db.query(User).filter(User.username == request.friend_username).first()
    if not friend:
        raise HTTPException(status_code=404, detail="Friend not found")
    if friend.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot add yourself")

    exists = (
        db.query(friendships)
        .filter(
            and_(
                friendships.c.user_id == current_user.id,
                friendships.c.friend_id == friend.id,
            )
        )
        .first()
    )
    if not exists:
        db.execute(friendships.insert().values(user_id=current_user.id, friend_id=friend.id))
        db.execute(friendships.insert().values(user_id=friend.id, friend_id=current_user.id))
        db.commit()

    return (
        db.query(User)
        .join(friendships, friendships.c.friend_id == User.id)
        .filter(friendships.c.user_id == current_user.id)
        .all()
    )


@app.get("/friends", response_model=list[UserOut])
def list_friends(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(User)
        .join(friendships, friendships.c.friend_id == User.id)
        .filter(friendships.c.user_id == current_user.id)
        .all()
    )


@app.post("/groups", response_model=GroupOut)
def create_group(
    payload: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group = ChatGroup(name=payload.name, owner_id=current_user.id)
    members = db.query(User).filter(User.id.in_(set(payload.member_ids + [current_user.id]))).all()
    group.members = members
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@app.get("/groups", response_model=list[GroupOut])
def list_groups(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ChatGroup).join(ChatGroup.members).filter(User.id == current_user.id).all()


@app.post("/messages/private", response_model=MessageOut)
async def send_private_message(
    payload: PrivateMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = Message(
        sender_id=current_user.id,
        receiver_id=payload.receiver_id,
        content=payload.content,
        image_url=payload.image_url,
        is_group_message=False,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    data = MessageOut.model_validate(message).model_dump(mode="json")
    await manager.send_to_user(payload.receiver_id, {"event": "private_message", "message": data})
    await manager.send_to_user(current_user.id, {"event": "private_message", "message": data})
    return message


@app.post("/messages/group", response_model=MessageOut)
async def send_group_message(
    payload: GroupMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group = db.query(ChatGroup).filter(ChatGroup.id == payload.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    message = Message(
        sender_id=current_user.id,
        group_id=payload.group_id,
        content=payload.content,
        image_url=payload.image_url,
        is_group_message=True,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    data = MessageOut.model_validate(message).model_dump(mode="json")
    for member in group.members:
        await manager.send_to_user(member.id, {"event": "group_message", "message": data})
    return message


@app.get("/messages/private/{friend_id}", response_model=list[MessageOut])
def private_history(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Message)
        .filter(
            and_(
                Message.is_group_message.is_(False),
                or_(
                    and_(Message.sender_id == current_user.id, Message.receiver_id == friend_id),
                    and_(Message.sender_id == friend_id, Message.receiver_id == current_user.id),
                ),
            )
        )
        .order_by(Message.created_at.asc())
        .all()
    )


@app.get("/messages/group/{group_id}", response_model=list[MessageOut])
def group_history(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group = db.query(ChatGroup).filter(ChatGroup.id == group_id).first()
    if not group or current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not allowed")
    return (
        db.query(Message)
        .filter(Message.group_id == group_id, Message.is_group_message.is_(True))
        .order_by(Message.created_at.asc())
        .all()
    )


@app.post("/upload")
def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename)[1]
    filename = f"{current_user.id}_{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename

    with filepath.open("wb") as f:
        f.write(file.file.read())

    return {"image_url": f"/uploads/{filename}"}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)


@app.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
