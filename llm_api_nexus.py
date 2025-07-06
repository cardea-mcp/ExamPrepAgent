import json
import requests
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from database.monogodb import MongoDB
from audio_processing.whisper_handler import whisper_handler

load_dotenv()
mongo_db = MongoDB()


NEXUS_BASE_URL = "http://localhost:9095/v1"

class LlamaNexusClient:
    def __init__(self):
        self.base_url = NEXUS_BASE_URL
        self.logger = logging.getLogger(__name__)
    
    def make_chat_completion_request(self, messages: List[Dict], tools: Optional[List] = None, tool_choice: str = "auto"):
        """Make chat completion request through llama-nexus"""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "model": "Qwen3-235B-A22B-Q4_K_M",  
            "messages": messages,
            "temperature": 0.7,
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        
        try:
            self.logger.info(f"Making request to llama-nexus: {url}")
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Llama-nexus request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Response text: {e.response.text}")
            raise Exception(f"Llama-nexus request failed: {str(e)}")

# Initialize client
nexus_client = LlamaNexusClient()

def format_context_for_llm(context):
    """Convert context list to formatted string for LLM"""
    if not context or (len(context) == 1 and not context[0]["user_query"]):
        return "No previous conversation history."
    
    formatted_context = "Previous conversation history:\n"
    for entry in context:
        if entry["user_query"]:
            formatted_context += f"User: {entry['user_query']}\n"
        if entry["agent_response"]:
            formatted_context += f"Assistant: {entry['agent_response']}\n"
        formatted_context += "\n"
    
    return formatted_context

async def process_message(session_id: str, user_input: str, available_functions: List = None):
    """Process a user message using llama-nexus with MCP tools"""
    
    session_context = mongo_db.get_session_context(session_id)
    context_string = format_context_for_llm(session_context)
    
    system_prompt = f"""You are a helpful AI assistant specialized in answering questions and providing practice questions. You have access to a tool that can find relevant information from a knowledge base.

Guidelines:
- ALWAYS call the  tool before answering any factual question
- For practice questions or random questions:
  * Ask user for  topic preferences
  * Search using topic keywords like "kubernetes" or "intermediate"
  * Present the question from search results and guide the learning process
- For specific questions:
  * Extract key terms from the user's question
  * Search using those keywords to find relevant information
  * Synthesize your answer based on the search results
- Be conversational and helpful
- If search returns multiple results, use the most relevant ones



Context from previous conversations:
{context_string}"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Add context messages (last 5 exchanges to keep context manageable)
    recent_context = session_context[-5:] if len(session_context) > 5 else session_context
    for entry in recent_context:
        if entry.get("user_query"):
            messages.append({"role": "user", "content": entry["user_query"]})
        if entry.get("agent_response"):
            messages.append({"role": "assistant", "content": entry["agent_response"]})
    
    # Add current user message
    messages.append({"role": "user", "content": user_input})
    
    try:
       
        completion_response = nexus_client.make_chat_completion_request(
            messages=messages,
            tool_choice="auto"
        )
        
        assistant_message = completion_response["choices"][0]["message"]
        response_text = assistant_message["content"]
        
        
        if "tool_calls" in assistant_message:
            logging.info(f"Tool calls made: {len(assistant_message['tool_calls'])}")
            for tool_call in assistant_message['tool_calls']:
                logging.info(f"Tool: {tool_call['function']['name']}, Args: {tool_call['function']['arguments']}")
        
        # Update session context
        new_context_entry = {
            "user_query": user_input,
            "agent_response": response_text,
            "tool_response": json.dumps(assistant_message.get("tool_calls", []))
        }
        
        session_context.append(new_context_entry)
        mongo_db.update_session_context(session_id, session_context)
        
        return response_text
        
    except Exception as e:
        logging.error(f"Error processing message: {str(e)}")
        return f"I apologize, but I encountered an error processing your request: {str(e)}"

async def process_audio_message(session_id: str, audio_data_wav: bytes, filename_wav: str, available_functions: List = None, language: Optional[str] = None):
    """Process an audio message using llama-nexus"""
    logger = logging.getLogger(__name__)
    
    try:
        if not audio_data_wav:
            return {
                "success": False,
                "error": "No audio data received for processing",
                "transcription": "",
                "response": ""
            }

        logger.info(f"Starting transcription for WAV data (filename: {filename_wav}) for session {session_id}")
        transcription_result = whisper_handler.transcribe_audio_bytes(audio_data_wav, filename_wav, language)
        
        if not transcription_result["success"]:
            return {
                "success": False,
                "error": f"Transcription failed: {transcription_result['error']}",
                "transcription": "",
                "response": ""
            }

        transcribed_text = transcription_result["text"]
        detected_language = transcription_result["language"]
        
        logger.info(f"Transcription successful: '{transcribed_text[:100]}...' (Language: {detected_language})")

        # Process through llama-nexus
        if transcribed_text.strip():
            response_text = await process_message(session_id, transcribed_text, available_functions)
            
            return {
                "success": True,
                "transcription": transcribed_text,
                "detected_language": detected_language,
                "response": response_text,
                "error": None
            }
        else:
            return {
                "success": True,
                "transcription": "",
                "detected_language": detected_language,
                "response": "I didn't detect any speech in your audio. Could you please try again?",
                "error": "No speech detected"
            }

    except Exception as e:
        logger.error(f"Audio message processing failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Internal error during audio processing: {str(e)}",
            "transcription": "",
            "response": ""
        }