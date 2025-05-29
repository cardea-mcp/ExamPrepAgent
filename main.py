from mcp.server.fastmcp import FastMCP
from utils.ques_select import get_random_qa, search_pair
import json
from utils.data import qa_pairs

mcp = FastMCP("Exam-Bot")

@mcp.tool()
def get_random_question(difficulty: str = None, topic: str = None):
    """
    Arguments: It takes the difficulty of the question and the topic of the question (both optional).
    Select a random question-answer pair from a list of question-answer pairs.
    Here the difficulty means that the level of which question complexity user wants. 
    The value of difficulty can be either 'beginner', 'intermediate', or 'advanced', or None for any difficulty.
    The topic can be any topic string or None for any topic.
    Returns:
    dict: A randomly selected dictionary containing a question and answer.
    """
    return get_random_qa(qa_pairs, difficulty, topic)

@mcp.tool()
def get_question_and_answer(question: str) -> str:
     """
     Search for relevant question and answer pair from the database.
     return the question and answer pair relevant to the question.
     """ 
     result = search_pair(question)
     return result

if __name__ == "__main__":
    mcp.run(transport="stdio")