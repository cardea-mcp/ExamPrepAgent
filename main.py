from fastmcp import FastMCP
from utils.ques_select import get_random_qa, search_pair
from typing import Dict, Any, List,Optional
import logging
from dotenv import load_dotenv
load_dotenv()
import os
host = os.getenv('MCP_HOST', '127.0.0.1')
port = int(os.getenv('MCP_PORT', 9096))
mcp = FastMCP("Exam-Bot")

logger = logging.getLogger(__name__)
@mcp.tool()
def get_random_question(topic: Optional[str] = None ):
    """
    It is used to get a random practice question from the database
    Arguments: It takes the topic of the question (optional).

    Returns:
    string : It returns a practice or random question for the given topic
    """
    print("using get_random_tool")
    result = get_random_qa(topic)
    print("Response from the tool: ", result)
    logger.info(f"here is the random result: {result}")
    return result 

@mcp.tool()
def get_question_and_answer(question: str) -> List[Dict[str, Any]]:
     """
     Search for relevant question and answer pair from the database.
     return the question and answer pair relevant to the question.
     """ 
     print("using get-question-tool")
     result = search_pair(question)
     logger.info(f"here is the get question and answer result: {result}")
     return result

if __name__ == "__main__":
    print("🚀 Starting MCP server...")
    mcp.run(
        transport="http",
        host=host,
        port=port,
        path="/mcp",
        log_level="debug",
    )
