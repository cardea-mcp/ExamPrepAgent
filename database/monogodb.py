import pymongo
import os
from dotenv import load_dotenv
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")


class MongoDB:
    def __init__(self, uri=MONGODB_URI):
        self.client = pymongo.MongoClient(MONGODB_URI)
        self.db = self.client['ExamBot']
        self.collection = self.db['exambotcontext']
    
    def get_user_context(self, user_id):
        """
        Retrieve user context from MongoDB
        
        Args:
            user_id (str): The unique identifier for the user
            
        Returns:
            list: List of dictionaries containing user_query, agent_response, and tool_response
        """
        user_record = self.collection.find_one({"user_id": user_id})
        if user_record:
            context = user_record.get("context", [])
            return context
        else:
            # Initialize context for new user
            initial_context = [{
                "user_query": "",
                "agent_response": "",
                "tool_response": ""
            }]
            self.update_user_context(user_id, initial_context)
            return initial_context
    
    def update_user_context(self, user_id, context):
        """
        Update user context in MongoDB
        
        Args:
            user_id (str): The unique identifier for the user
            context (list): List of dictionaries with user_query, agent_response, and tool_response
            
        Returns:
            bool: True if update was successful
        """
        self.collection.update_one(
            {"user_id": user_id},
            {"$set": {"context": context}},
            upsert=True
        )
        # print("The context has been updated ---------- \n", context)
        return True