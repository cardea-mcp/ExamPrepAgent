from mcp.server.fastmcp import FastMCP
from ques_select import get_random_qa, search_pair
import json
with open('file.json','r') as f:
    q_list = json.load(f)
mcp = FastMCP("Exam-Bot")

@mcp.tool()
def get_random_question():
    """
    Select a random question-answer pair from a list of question-answer pairs.
    
    Returns:
    dict: A randomly selected dictionary containing a question and answer.
    """
    return get_random_qa(q_list)

@mcp.tool()
def get_question_and_answer(question:str) -> str:
     """
     Search for relevant question and answer pair from the database.
     return the question and answer pair relevant to the question.
     """ 
     result = search_pair(question)
    #  print(result)
     return result

if __name__ == "__main__":
    mcp.run(transport="stdio")