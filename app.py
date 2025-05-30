# app.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from database.monogodb import MongoDB
from llm_api import initialize_mcp_server, process_message, cleanup_server
import atexit

app = FastAPI(title="ExamBOT API")


mongo_db = MongoDB()
available_functions = initialize_mcp_server()


atexit.register(cleanup_server)


app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models
class UserCreate(BaseModel):
    name: str

class MessageSend(BaseModel):
    message: str

class SessionCreate(BaseModel):
    name: Optional[str] = None

class SessionUpdate(BaseModel):
    name: str

# API Routes
@app.post("/api/users")
async def create_user(user: UserCreate):
    """Create or get a user"""
    user_id = mongo_db.create_user(user.name)
    return {"user_id": user_id, "name": user.name}

@app.get("/api/users/{user_name}")
async def get_user(user_name: str):
    """Get user by name"""
    user = mongo_db.get_user_by_name(user_name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/users/{user_id}/sessions")
async def create_session(user_id: str, session: SessionCreate):
    """Create a new chat session"""
    session_id = mongo_db.create_session(user_id, session.name)
    return {"session_id": session_id}

@app.get("/api/users/{user_id}/sessions")
async def get_user_sessions(user_id: str):
    """Get all sessions for a user"""
    sessions = mongo_db.get_user_sessions(user_id)
    return {"sessions": sessions}

@app.get("/api/sessions/{session_id}")
async def get_session_context(session_id: str):
    """Get session context/chat history"""
    context = mongo_db.get_session_context(session_id)
    return {"context": context}

@app.post("/api/sessions/{session_id}/messages")
async def send_message(session_id: str, message: MessageSend):
    """Send a message to the chatbot"""
    try:
        response = await process_message(session_id, message.message, available_functions)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    success = mongo_db.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully"}

@app.put("/api/sessions/{session_id}")
async def update_session(session_id: str, update: SessionUpdate):
    """Update session name"""
    success = mongo_db.update_session_name(session_id, update.name)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session updated successfully"}

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main HTML page"""
    with open("static/index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)