from typing import Optional, Dict, Any, List
from database.tidb import tidb_client

def get_random_qa(topic: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Select a random question-answer pair with optional filtering using TiDB full-text search.
    
    Parameters:
    topic (str, optional): Search term for full-text search (e.g., 'node controller', 'networking').
    
    Returns:
    dict: A randomly selected dictionary containing question, answer, or None if no matches found.
    """
    return tidb_client.get_random_qa(topic=topic)

def search_pair(query_text: str) -> List[Dict[str, Any]]:
    """
    Search for relevant question and answer pairs from TiDB using full-text search.
    
    Parameters:
    query_text (str): The search query
    
    Returns:
    list: List of relevant Q&A pairs with relevance scores
    """
    return tidb_client.search_pair(query_text)

