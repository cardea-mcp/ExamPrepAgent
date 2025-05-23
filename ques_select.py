import random
import json
from qdrant import client
from encoder import create_embedding





def get_random_qa(qa_list):
    """
    Select a random question-answer pair from a list of dictionaries.
    
    Parameters:
    qa_list (list): A list of dictionaries, where each dictionary has 'question' and 'answer' keys.
    
    Returns:
    dict: A randomly selected dictionary containing a question and answer.
    """
    if not qa_list:
        return None
    
    return random.choice(qa_list)

def search_pair(query_text):
    # Create embedding for the query
    query_embedding = create_embedding(query_text)
    
    # Search in Qdrant
    search_results = client.search(
        collection_name="mining_qa",
        query_vector=query_embedding,
        limit=3  # Return top 3 matches
    )
    
    # Return the complete Q&A pairs
    return [{
        "question": result.payload["question"],
        "answer": result.payload["answer"],
        "score": result.score
    } for result in search_results]   


