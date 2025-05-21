from mcp.server.fastmcp import FastMCP
from ques_select import get_random_qa, search_pair
mcp = FastMCP("Exam-Bot")


import json

with open('file.json','r') as f:
    q_list = json.load(f)
    
@mcp.tool()
def get_random_question():
    return get_random_qa(q_list)

@mcp.tool()
def get_question_and_answer(question:str):
     result = search_pair(question)
     print(result)
     return result

if __name__ == "__main__":
    mcp.run(transport="stdio")