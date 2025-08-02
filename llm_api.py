import json
import os
import requests
from dotenv import load_dotenv
load_dotenv()
from audio_processing.whisper_handler import whisper_handler
import logging
import time
from llmclient import client
from database.tidb import tidb_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


HTTP_LOGGING_ENABLED = os.getenv('HTTP_LOGGING_ENABLED', 'false').lower() == 'true'
HTTP_LOG_LEVEL = os.getenv('HTTP_LOG_LEVEL', 'INFO')
HTTP_LOG_FILE = os.getenv('HTTP_LOG_FILE', 'http_logs.log')
HTTP_LOG_TRUNCATE_PAYLOAD = int(os.getenv('HTTP_LOG_TRUNCATE_PAYLOAD', 5000))
HTTP_LOG_TRUNCATE_RESPONSE = int(os.getenv('HTTP_LOG_TRUNCATE_RESPONSE', 3000))


http_logger = logging.getLogger('http_requests')

if HTTP_LOGGING_ENABLED:
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler = logging.FileHandler(HTTP_LOG_FILE)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, HTTP_LOG_LEVEL))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter) 
    http_logger.setLevel(getattr(logging, HTTP_LOG_LEVEL))
    console_handler.setLevel(getattr(logging, HTTP_LOG_LEVEL))
    
    # Add handler to logger
    http_logger.addHandler(console_handler)
    http_logger.addHandler(file_handler)
    # Prevent duplicate logs from parent loggers
    http_logger.propagate = False
else:
    http_logger.disabled = True

API_BASE_URL = os.getenv('BASE_URL')
API_KEY = os.getenv('API_KEY')
SYSTEM_PROMPT = os.getenv('SYSTEM_PROMPT')

def mask_sensitive_data(headers):
    """Mask sensitive data in headers for logging"""
    masked_headers = headers.copy()
    if 'Authorization' in masked_headers:
        auth_value = masked_headers['Authorization']
        if auth_value.startswith('Bearer '):
            token = auth_value[7:]  
            if len(token) > 10:
                masked_token = token[:10] + '*' * (len(token) - 10)
                masked_headers['Authorization'] = f'Bearer {masked_token}'
    return masked_headers

def log_http_request(url, headers, payload, method="POST"):
    """Log detailed HTTP request information"""
    if not HTTP_LOGGING_ENABLED:
        return
        
    http_logger.info("="*60)
    http_logger.info("OUTGOING HTTP REQUEST")
    http_logger.info("="*60)
    http_logger.info(f"Method: {method}")
    http_logger.info(f"URL: {url}")
    
    masked_headers = mask_sensitive_data(headers)
    http_logger.info("Headers:")
    for key, value in masked_headers.items():
        http_logger.info(f"  {key}: {value}")

    http_logger.info("Request Payload:")
    if isinstance(payload, dict):
        formatted_payload = json.dumps(payload, indent=2, ensure_ascii=False)
        if len(formatted_payload) > HTTP_LOG_TRUNCATE_PAYLOAD:
            http_logger.info(f"{formatted_payload[:HTTP_LOG_TRUNCATE_PAYLOAD]}... [TRUNCATED]")
        else:
            http_logger.info(formatted_payload)
    else:
        http_logger.info(f"  {payload}")
    
    http_logger.info("="*60)

def log_http_response(response, response_data=None):
    """Log HTTP response information"""
    http_logger.info("INCOMING HTTP RESPONSE")
    http_logger.info("="*60)
    http_logger.info(f"Status Code: {response.status_code}")
    http_logger.info(f"Status Text: {response.reason}")
    
    http_logger.info("Response Headers:")
    for key, value in response.headers.items():
        http_logger.info(f"  {key}: {value}")
    
    http_logger.info("Response Body:")
    if response_data:
        if isinstance(response_data, dict):
            formatted_response = json.dumps(response_data, indent=2, ensure_ascii=False)
            if len(formatted_response) > 3000:
                http_logger.info(f"{formatted_response[:3000]}... [TRUNCATED]")
            else:
                http_logger.info(formatted_response)
        else:
            http_logger.info(f"  {response_data}")
    else:
        # Fallback to raw text
        try:
            text_content = response.text
            if len(text_content) > 3000:
                http_logger.info(f"{text_content[:3000]}... [TRUNCATED]")
            else:
                http_logger.info(text_content)
        except:
            http_logger.info("  [Unable to decode response body]")
    
    http_logger.info("="*60)

def make_chat_completion_request(messages, tools=None, tool_choice="auto"):
    """Make a direct API request to chat completions endpoint with detailed logging"""
    url = f"{API_BASE_URL}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}" if API_KEY.strip() else "Bearer dummy"
    }
    
    payload = {
        "model": os.getenv('LLM_MODEL'),
        "messages": messages,
        "temperature": 0.7,
        "tool_choice": "auto" 
    }
    
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice
    
    try:
        log_http_request(url, headers, payload)
        
        http_logger.info("🚀 Sending HTTP request...")
        start_time = time.time()
        
        response = requests.post(
            url, 
            headers=headers, 
            data=json.dumps(payload), 
            timeout=6000
        )
        
        end_time = time.time()
        request_duration = end_time - start_time
        
        http_logger.info(f"⏱️  Request completed in {request_duration:.2f} seconds")

        response_data = None
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            http_logger.warning("Could not parse response as JSON")
        
        log_http_response(response, response_data)
        
        response.raise_for_status()
        return response_data if response_data else response.json()
        
    except requests.exceptions.RequestException as e:
        http_logger.error(f"❌ API request failed: {str(e)}")
        if 'response' in locals():
            log_http_response(response)
        raise Exception(f"API request failed: {str(e)}")

async def get_tools():
    """Get available tools using FastMCP client"""
    try:
        async with client:
            tools_response = await client.list_tools()
            available_functions = []
            
            for tool in tools_response:
                func = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            "type": "object",
                            "properties": tool.inputSchema.get("properties", {}),
                            "required": tool.inputSchema.get("required", []),
                        },
                    },
                }
                available_functions.append(func)
            
            return available_functions
    except Exception as e:
        print(f"Error getting tools: {str(e)}")
        return []


async def handle_tool_calls(tool_calls):
    """Handle tool calls using FastMCP client"""
    tool_responses = []
    
    try:
        async with client:
            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"]) if isinstance(tool_call["function"]["arguments"], str) else tool_call["function"]["arguments"]
                
                print(f"Calling tool: {function_name} with args: {function_args}")
                
                # Call tool using FastMCP client
                tool_result = await client.call_tool(name=function_name, arguments=function_args)
                
                result_text = ""
                
                if hasattr(tool_result, 'content') and tool_result.content:
                    for content in tool_result.content:
                        if hasattr(content, 'text'):
                            result_text += content.text
                elif hasattr(tool_result, 'structured_content') and tool_result.structured_content:
                    result_text = json.dumps(tool_result.structured_content)
                else:
                    result_text = "No result"
                
                tool_responses.append({
                    "tool_call_id": tool_call["id"],
                    "role": "tool",
                    "name": function_name,
                    "content": result_text
                })
        
        return tool_responses
    except Exception as e:
        print(f"Error handling tool calls: {str(e)}")
        return []


async def process_message(session_id, user_input):
    """Process a user message and return the response"""
    logger = logging.getLogger(__name__)
    logger.info(f"session id {session_id}")
    available_functions = await get_tools()

    session_context = tidb_client.get_session_context(session_id)
    logger.info(f"type of session_context: {type(session_context)}")
    logger.info(f"Session context: {session_context}")
    
    messages = [
        {"role": "system", "content": f"""{SYSTEM_PROMPT}
"""}
    ]
    
    for entry in session_context:
        if entry.get("user_query"):
            messages.append({"role": "user", "content": entry["user_query"]})
        

        if entry.get("tool_calls") and entry.get("tool_responses"):
            messages.append({
                "role": "assistant",
                "content": entry.get("assistant_content"),  # This might be null/empty for tool calls
                "tool_calls": entry["tool_calls"]
            })
            
            # Add tool response messages
            for tool_response in entry["tool_responses"]:
                messages.append(tool_response)
                
        if entry.get("agent_response"):
            messages.append({"role": "assistant", "content": entry["agent_response"]})
    
    messages.append({"role": "user", "content": user_input})
    
    completion_response = make_chat_completion_request(
        messages=messages,
        tools=available_functions,
        tool_choice="auto"
    )
    
    assistant_message = completion_response["choices"][0]["message"]
    tool_calls = None
    tool_responses = []
    tool_response_content = ""
    
    if assistant_message.get("tool_calls"):
        tool_calls = assistant_message["tool_calls"]
        tool_responses = await handle_tool_calls(assistant_message["tool_calls"])
        tool_response_content = json.dumps([resp["content"] for resp in tool_responses])
        
        messages.append({
            "role": "assistant",
            "content": assistant_message.get("content"),
            "tool_calls": assistant_message["tool_calls"]
        })
        
        # Add tool responses
        for tool_response in tool_responses:
            messages.append(tool_response)
        
        final_completion_response = make_chat_completion_request(
            messages=messages,
            tools=available_functions,
            tool_choice="auto"
        )
        
        final_message = final_completion_response["choices"][0]["message"]
        response_text = final_message["content"]
    else:
        response_text = assistant_message["content"]
    
    # Update session context with complete structure
    new_context_entry = {
        "user_query": user_input,
        "agent_response": response_text,
        "tool_response": tool_response_content,  # Keep for backward compatibility
        "tool_calls": tool_calls, 
        "tool_responses": tool_responses,  # Store the tool responses
        "assistant_content": assistant_message.get("content") if tool_calls else None
    }
    
    session_context.append(new_context_entry)
    tidb_client.update_session_context(session_id, session_context)
    
    return response_text

async def process_audio_message(session_id, audio_data_wav, filename_wav, available_functions, language=None):
    """Process an audio message and return the response"""
    logger = logging.getLogger(__name__)
    
    try:
        if not audio_data_wav:
            return { "success": False, "error": "No audio data received for processing", "transcription": "", "response": ""}

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

        # Process the transcribed text through the normal message pipeline
        if transcribed_text.strip():
            response_text = await process_message(session_id, transcribed_text)
            
            return {
                "success": True,
                "transcription": transcribed_text,
                "detected_language": detected_language,
                "response": response_text,
                "error": None
            }
        else:
            logger.info("Transcription resulted in empty text (possibly silence).")
            return {
                "success": True, # Transcription itself didn't fail, just no speech
                "transcription": "",
                "detected_language": detected_language,
                "response": "I didn't detect any speech in your audio. Could you please try again?",
                "error": "No speech detected"
            }

    except Exception as e:
        logger.error(f"Audio message processing failed in llm_api: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Internal error during audio processing: {str(e)}",
            "transcription": "",
            "response": ""
        }

def cleanup_server():
    """Cleanup function (no longer needed with FastMCP client)"""
    pass

