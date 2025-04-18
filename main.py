import os
from typing import Dict, Optional
from src.models import ChatRequest, ChatResponse, SessionState
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from src.mcp_client import MCPClient

# Initialize FastAPI app
app = FastAPI(title="MCP Chatbot API", description="API for interacting with a chatbot using MCP")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Global state management
active_sessions: Dict[str, Dict] = {}
mcp_client = None
server_connected = False

# Session management
def get_or_create_session(session_id: Optional[str] = None) -> tuple[str, SessionState]:
    """Get or create a chat session"""
    import uuid
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    if session_id not in active_sessions:
        active_sessions[session_id] = {"state": SessionState()}
    
    return session_id, active_sessions[session_id]["state"]

# Initialization and shutdown
@app.on_event("startup")
async def startup_event():
    global mcp_client, server_connected
    
    mcp_client = MCPClient()
    try:
        server_script = os.getenv("MCP_SERVER_SCRIPT", "src/mcp-server-sqlite.py")
        tools = await mcp_client.connect_to_server(server_script)
        server_connected = True
        print(f"MCP server connected successfully with tools: {tools}")
    except Exception as e:
        print(f"Failed to connect to MCP server: {str(e)}")
        server_connected = False

@app.on_event("shutdown")
async def shutdown_event():
    global mcp_client
    if mcp_client:
        await mcp_client.cleanup()

# API endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "MCP Chatbot API is running", "status": "connected" if server_connected else "disconnected"}

@app.get("/status")
async def status():
    """Get server status"""
    global server_connected
    return {
        "server_connected": server_connected,
        "active_sessions": len(active_sessions),
        "tools": [tool.name for tool in mcp_client.tools] if mcp_client and mcp_client.tools else []
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest, background_tasks: BackgroundTasks):
    """Process a chat request"""
    global mcp_client, server_connected
    
    if not server_connected or not mcp_client or not mcp_client.session:
        # Try to reconnect
        try:
            server_script = os.getenv("MCP_SERVER_SCRIPT", "src/mcp-server-sqlite.py")
            await mcp_client.connect_to_server(server_script)
            server_connected = True
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"MCP server not connected: {str(e)}")
    
    # Get or create session
    session_id, session_state = get_or_create_session(chat_request.session_id)
    
    try:
        # Add user message to history
        session_state.messages.append({"role": "user", "content": chat_request.query})
        
        # Process the query
        response = await mcp_client.process_query(
            chat_request.query, 
            chat_history=session_state.messages[:-1]  # Exclude the current message
        )
        
        # Add assistant response to history
        session_state.messages.append({"role": "assistant", "content": response})
        
        # Clean up old sessions in the background
        background_tasks.add_task(clean_old_sessions)
        
        return ChatResponse(response=response, session_id=session_id)
    
    except Exception as e:
        # If there's an error, don't save the failed interaction in history
        session_state.messages.pop()  # Remove the user message
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """Get chat history for a session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"session_id": session_id, "messages": active_sessions[session_id]["state"].messages}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del active_sessions[session_id]
    return {"message": f"Session {session_id} deleted successfully"}

# Maintenance tasks
async def clean_old_sessions():
    """Clean up old or inactive sessions"""
    # In a real application, you would remove sessions that have been inactive for a while
    # For simplicity, we're just capping the total number of sessions
    MAX_SESSIONS = 100
    
    if len(active_sessions) > MAX_SESSIONS:
        # Remove oldest sessions first (simple implementation)
        sessions_to_remove = list(active_sessions.keys())[:(len(active_sessions) - MAX_SESSIONS)]
        for session_id in sessions_to_remove:
            del active_sessions[session_id]

# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000)