import os
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from pytidb import TiDBClient
from pytidb.schema import TableModel, Field
from sqlalchemy import text , TEXT , Column , JSON

load_dotenv()

class User(TableModel, table=True):
    __tablename__ = "users"
    
    id: str = Field(primary_key=True, max_length=36)
    name: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ChatSession(TableModel, table=True):
    __tablename__ = "chat_sessions"
    
    id: str = Field(primary_key=True, max_length=36)
    user_id: str = Field(max_length=36)
    session_name: str = Field(max_length=255)
    context: str = Field()  # Simple dict type - TiDB will handle JSON automatically
    created_at: datetime = Field()
    updated_at: datetime = Field()

class TiDBChat:
    def __init__(self):
        self.db = None
        self.users_table = None
        self.sessions_table = None
        self.connect()
    
    def connect(self):
        """Connect to TiDB Cloud for chat management"""
        try:
            self.db = TiDBClient.connect(
                host=os.getenv("TIDB_HOST"),
                port=int(os.getenv("TIDB_PORT", 4000)),
                username=os.getenv("TIDB_USERNAME"),
                password=os.getenv("TIDB_PASSWORD"),
                database=os.getenv("TIDB_DATABASE"),
            )
            
            # Create tables
            user_table = User.__tablename__
            session_table = ChatSession.__tablename__
            if not self.db.has_table(user_table):
                print(f"🛠️ Table '{user_table}' does not exist. Creating it now...")
                self.users_table = self.db.create_table(schema=User)
            else:
                print(f"📦 Table '{user_table}' exists. Opening it...")
                self.users_table = self.db.open_table(user_table)
            
            self.sessions_table = self.db.open_table("chat_sessions")
            
            
            
            print("✅ Connected to TiDB for chat management!")
            
        except Exception as e:
            print(f"❌ Failed to connect to TiDB for chat: {str(e)}")
            raise e
    
    def create_user(self, user_name: str) -> str:
        """Create a new user or get existing user"""
        try:
            # Check if user already exists
            existing_users = self.users_table.query(filters={'name': user_name})
            if existing_users:
                return existing_users[0].id
            
            # Create new user
            user_id = str(uuid.uuid4())
            user = User(
                id=user_id,
                name=user_name,
                created_at=datetime.utcnow()
            )
            
            self.users_table.insert(user)
            return user_id
            
        except Exception as e:
            print(f"❌ Error creating user: {str(e)}")
            raise e
    
    def create_session(self, user_id: str, session_name: Optional[str] = None) -> str:
        """Create a new chat session for a user"""
        try:
            session_id = str(uuid.uuid4())
            
            if not session_name:
                session_name = f"Chat {datetime.utcnow().strftime('%m/%d %H:%M')}"
            
            session = ChatSession(
                id=session_id,
                user_id=user_id,
                session_name=session_name,
                context="[]",  # Empty JSON array as string
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.sessions_table.insert(session)
            return session_id
            
        except Exception as e:
            print(f"❌ Error creating session: {str(e)}")
            raise e
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        try:
            sessions = self.sessions_table.query(filters={'user_id': user_id})
            
            # Convert to dict format and sort by updated_at desc
            sessions_list = []
            for session in sessions:
                sessions_list.append({
                    '_id': session.id,
                    'session_name': session.session_name,
                    'created_at': session.created_at.isoformat(),
                    'updated_at': session.updated_at.isoformat()
                })
            
            sessions_list.sort(key=lambda x: x['updated_at'], reverse=True)
            return sessions_list
            
        except Exception as e:
            print(f"❌ Error loading sessions: {str(e)}")
            return []
    
    def get_session_context(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve session context from TiDB"""
        try:
            sessions = self.sessions_table.query(filters={'id': session_id})
            if sessions:
                import json
                context_str = sessions[0].context
                return json.loads(context_str) if context_str else []
            else:
                return []
                
        except Exception as e:
            print(f"❌ Error getting session context: {str(e)}")
            return []
    
    def update_session_context(self, session_id: str, context: List[Dict[str, Any]]) -> bool:
        """Update session context in TiDB"""
        try:
            import json
            context_json = json.dumps(context)
            
            with self.db.session() as session:
                update_query = text("""
                    UPDATE chat_sessions 
                    SET context = :context, updated_at = :updated_at 
                    WHERE id = :session_id
                """)
                session.execute(update_query, {
                    'context': context_json,
                    'updated_at': datetime.utcnow(),
                    'session_id': session_id
                })
                session.commit()
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating session context: {str(e)}")
            return False
    
    def get_user_by_name(self, user_name: str) -> Optional[Dict[str, Any]]:
        """Get user by name"""
        try:
            users = self.users_table.query(filters={'name': user_name})
            if users:
                user = users[0]
                return {
                    '_id': user.id,
                    'name': user.name,
                    'created_at': user.created_at.isoformat()
                }
            return None
            
        except Exception as e:
            print(f"❌ Error getting user by name: {str(e)}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        try:
            with self.db.session() as session:
                delete_query = text("DELETE FROM chat_sessions WHERE id = :session_id")
                result = session.execute(delete_query, {'session_id': session_id})
                session.commit()
                return result.rowcount > 0
            
        except Exception as e:
            print(f"❌ Error deleting session: {str(e)}")
            return False
    
    def update_session_name(self, session_id: str, new_name: str) -> bool:
        """Update session name"""
        try:
            with self.db.session() as session:
                update_query = text("""
                    UPDATE chat_sessions 
                    SET session_name = :new_name, updated_at = :updated_at 
                    WHERE id = :session_id
                """)
                result = session.execute(update_query, {
                    'new_name': new_name,
                    'updated_at': datetime.utcnow(),
                    'session_id': session_id
                })
                session.commit()
                return result.rowcount > 0
            
        except Exception as e:
            print(f"❌ Error updating session name: {str(e)}")
            return False