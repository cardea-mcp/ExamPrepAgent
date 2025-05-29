import random
import json
from vectorstore.qdrant import client
from encoder.encoder import create_embedding

import random

def get_random_qa(qa_list, difficulty=None, topic=None):
    """
    Select a random question-answer pair from a list of dictionaries with optional filtering.
    
    Parameters:
    qa_list (list): A list of dictionaries, where each dictionary has 'question', 'answer', 'topic', 'type', and 'difficulty' keys.
    difficulty (str, optional): Filter by difficulty level (e.g., 'beginner', 'intermediate', 'advanced').
    topic (str, optional): Filter by topic (e.g., 'architecture', 'control plane').
    
    Returns:
    dict: A randomly selected dictionary containing question, answer, and other fields, or None if no matches found.
    """
    if not qa_list:
        return None
    
    # Filter the list based on provided criteria
    filtered_list = qa_list.copy()
    
    if difficulty:
        filtered_list = [qa for qa in filtered_list if qa.get('difficulty', '').lower() == difficulty.lower()]
    
    if topic:
        filtered_list = [qa for qa in filtered_list if qa.get('topic', '').lower() == topic.lower()]
    
    # Return None if no questions match the criteria
    if not filtered_list:
        return None
    
    return random.choice(filtered_list)
def search_pair(query_text):
    # Create embedding for the query
    query_embedding = create_embedding(query_text)
    
    # Search in Qdrant
    search_results = client.search(
        collection_name="kubernetes_qa",
        query_vector=query_embedding,
        limit=3  # Return top 3 matches
    )
    
    # Return the complete Q&A pairs
    return [{
        "question": result.payload["question"],
        "answer": result.payload["answer"],
        "topic": result.payload["topic"],
        "type": result.payload["type"],
        "difficulty": result.payload["difficulty"],
        "score": result.score
    } for result in search_results]   


