# database/monogodb.py
import pymongo
import os
from dotenv import load_dotenv
from datetime import datetime
import uuid
from bson import ObjectId

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")


class MongoDB:
    def __init__(self, uri=MONGODB_URI):
        self.client = pymongo.MongoClient(MONGODB_URI)
        self.db = self.client['ExamBot']
        self.users_collection = self.db['users']
        self.sessions_collection = self.db['sessions']
    
    def create_user(self, user_name):
        """
        Create a new user or get existing user
        
        Args:
            user_name (str): The name of the user
            
        Returns:
            str: User ID
        """
        user = self.users_collection.find_one({"name": user_name})
        if user:
            return str(user['_id'])
        else:
            user_doc = {
                "name": user_name,
                "created_at": datetime.utcnow()
            }
            result = self.users_collection.insert_one(user_doc)
            return str(result.inserted_id)
    
    def create_session(self, user_id, session_name=None):
        """
        Create a new chat session for a user
        
        Args:
            user_id (str): The unique identifier for the user
            session_name (str): Optional name for the session
            
        Returns:
            str: Session ID
        """
        if not session_name:
            session_name = f"Chat {datetime.utcnow().strftime('%m/%d %H:%M')}"
        
        session_doc = {
            "user_id": user_id,
            "session_name": session_name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "context": []
        }
        result = self.sessions_collection.insert_one(session_doc)
        return str(result.inserted_id)
    
    def get_user_sessions(self, user_id):
        """
        Get all sessions for a user
        
        Args:
            user_id (str): The unique identifier for the user
            
        Returns:
            list: List of sessions
        """
        sessions = list(self.sessions_collection.find(
            {"user_id": user_id}, 
            {"session_name": 1, "created_at": 1, "updated_at": 1}
        ).sort("updated_at", -1))
        
        for session in sessions:
            session['_id'] = str(session['_id'])
        
        return sessions
    
    def get_session_context(self, session_id):
        """
        Retrieve session context from MongoDB
        
        Args:
            session_id (str): The unique identifier for the session
            
        Returns:
            list: List of dictionaries containing user_query, agent_response, and tool_response
        """
        session = self.sessions_collection.find_one({"_id": ObjectId(session_id)})
        if session:
            return session.get("context", [])
        else:
            return []
    
    def update_session_context(self, session_id, context):
        """
        Update session context in MongoDB
        
        Args:
            session_id (str): The unique identifier for the session
            context (list): List of dictionaries with user_query, agent_response, and tool_response
            
        Returns:
            bool: True if update was successful
        """
        self.sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "context": context,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return True
    
    def get_user_by_name(self, user_name):
        """
        Get user by name
        
        Args:
            user_name (str): The name of the user
            
        Returns:
            dict: User document or None
        """
        user = self.users_collection.find_one({"name": user_name})
        if user:
            user['_id'] = str(user['_id'])
        return user
    
    def delete_session(self, session_id):
        """
        Delete a session
        
        Args:
            session_id (str): The unique identifier for the session
            
        Returns:
            bool: True if deletion was successful
        """
        result = self.sessions_collection.delete_one({"_id": ObjectId(session_id)})
        return result.deleted_count > 0
    
    def update_session_name(self, session_id, new_name):
        """
        Update session name
        
        Args:
            session_id (str): The unique identifier for the session
            new_name (str): New name for the session
            
        Returns:
            bool: True if update was successful
        """
        result = self.sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "session_name": new_name,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0