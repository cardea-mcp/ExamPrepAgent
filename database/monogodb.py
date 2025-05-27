
import pymongo
from config import MONGODB_URI, MONGODB_DB, MONGODB_COLLECTION

class MongoDB:
    def __init__(self, uri=MONGODB_URI):
        self.client = pymongo.MongoClient(MONGODB_URI)
        self.db = self.client['rustsmith']
        self.collection = self.db['user_contexts']
    
    def get_user_context(self, user_id):
        """
        Retrieve user context from MongoDB
        
        Args:
            user_id (str): The unique identifier for the user
            
        Returns:
            list: List of dictionaries containing question, answer, and error
        """
        user_record = self.collection.find_one({"user_id": user_id})
        if user_record:
            context = user_record.get("context", [])
            if context:
                return context[-1]
        return []
    
    def update_user_context(self, user_id, context):
        """
        Update user context in MongoDB
        
        Args:
            user_id (str): The unique identifier for the user
            context (list): List of dictionaries with question, answer, and error
            
        Returns:
            bool: True if update was successful
        """
        self.collection.update_one(
            {"user_id": user_id},
            {"$set": {"context": context}},
            upsert=True
        )
        print("The context has been updated ---------- \n",context)
        return True

