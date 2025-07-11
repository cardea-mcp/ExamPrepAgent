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
    logger = logging.getLogger(__name__)
    session_context = mongo_db.get_session_context(session_id)
    recent_context = session_context[-5:] if len(session_context) > 5 else session_context
    context_string = format_context_for_llm(recent_context)
    
    system_prompt = f"""If the user asks a question, you MUST use tool and pass in a list of search keywords to search for relevant information and then form your response based on the search results.
   
    You will also be given previous interaction with the user and the assistant. You can use this context to guide your response. 

    Guidelines:
    1. When user has asked a practice question or random question to practice you will get the result from the tool with question and answer, but you have to tell the user only the question.
    2. When user will say something which means he didn't know the answer to the practice question, you will tell him the answer to that question using the tool.
Context from previous conversations:
{context_string}"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Add current user message
    messages.append({"role": "user", "content": user_input})
    
    try:
       
        completion_response = nexus_client.make_chat_completion_request(
            messages=messages,
            # tool_choice="auto"
        )
        logger.info(f"The completion response is \n {completion_response}")
        assistant_message = completion_response["choices"][0]["message"]
        response_text = assistant_message["content"]
        logger.info(f"The  response is \n{response_text}")


        new_context_entry = {
            "user_query": user_input,
            "agent_response": response_text
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
