# Mini WeChat-like Messaging App

A full-stack mini messaging app with:

- User accounts (register/login)
- Add friends
- Private chat
- Group chat
- Message history
- Image upload
- Realtime message delivery with WebSocket

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy
- **Database**: PostgreSQL
- **Realtime**: FastAPI WebSocket
- **Frontend**: React (Vite)

## Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create PostgreSQL DB:

```sql
CREATE DATABASE wechat_clone;
```

Update DB URL in `backend/app/database.py` if needed.

Run backend:

```bash
uvicorn app.main:app --reload --port 8000
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173` and expects backend at `http://localhost:8000`.

## Key API Endpoints

- `POST /auth/register`
- `POST /auth/login`
- `POST /friends/add`
- `GET /friends`
- `POST /groups`
- `GET /groups`
- `POST /messages/private`
- `POST /messages/group`
- `GET /messages/private/{friend_id}`
- `GET /messages/group/{group_id}`
- `POST /upload`
- `GET /ws/{user_id}`
