# 🧠 Exam-BOT (MCP-Based AI Agent for LF Certificate Prep)

A prototype AI agent built using the **Model Context Protocol (MCP)** to assist students preparing for **Linux Foundation (LF) certifications** through interactive practice questions and intelligent Q&A responses.

---

Here is the demo video of bot in action: 
https://www.loom.com/share/e11263ab6c3e4a4da33e5e2b726cfd80?sid=173cf35a-8447-4666-b374-a78f5c5193d4
## 🚀 Project Overview

This project serves as an intelligent study companion leveraging **open-source Large Language Models (LLMs)** and **MCP servers** to provide an engaging and interactive learning experience. The agent supports:

- Random practice questions
- Semantic search of relevant Q&A pairs
- Guided conversation for deeper understanding

---

ScreenShots of the bot in action
![Bot giving practicing question to the user](public/lfx_exambot_ui_sc.png)

 ### **Here in the above image, you can see that the bot is asking the user about the complexity level of question he wants to practice. The bot is also asking the topic he wants to prepare.** 

### **In this way the practicing for the exam becomes more personal and engaging.**
---

For this prototype I have created two datasets:
- **Kubernetes-Q&A** - A collection of Q&A pairs focused on Kubernetes and cloud native concepts. It is uploaded to my hugging face id. 
here is the link to the dataset. https://huggingface.co/datasets/ItshMoh/kubernetes_qa_pairs . It contains 497 Q&A pairs. It has also crossed **45 downloads** on hugging face.
It is made for KCNA exam. Contents are taken from the kubernetes.io licensed under CC BY 4.0

- **Metal-mining-Q&A** - A collection of Q&A pairs focused on metal mining methods. The link to the dataset https://huggingface.co/datasets/ItshMoh/metal-mining-qa-pairs . It has also more than 31 downloads on hugging face.
## 🏗️ Architecture

### 🔧 Key Files Description

#### Core Application Files

`app.py` vs `app_nexus.py`

`app.py`: Direct API integration architecture

- Communicates directly with LLM APIs (OpenAI-compatible)
- Manages MCP server subprocess internally
- Suitable for direct API deployments


`app_nexus.py`: Llama-Nexus integration architecture

- Routes requests through Llama-Nexus gateway
- Llama-Nexus handles MCP tool calls automatically
- Better for complex multi-agent scenarios

#### LLM Integration Files

`llm.py` - Command Line Interface
- Interactive CLI chat interface
- Direct MCP server communication
- User context management via MongoDB
- Manual tool calling workflow

`llm_api.py` - FastAPI Integration (Direct)

- HTTP API endpoint integration
- Subprocess MCP server management
- Audio message processing
- Session-based context handling

`llm_api_nexus.py` - Llama-Nexus Integration
- Llama-Nexus HTTP client
- Automatic MCP tool routing
- Simplified tool calling (handled by Nexus)
- Enhanced error handling

#### MCP & Database

`main.py` - MCP Server
- Implements FastMCP server
- Provides get_random_question() and get_question_and_answer() tools
- Interfaces with TiDB for full-text search
The system is composed of several core components:

`database/tidb.py` - TiDB Integration

- Vector similarity search
- Full-text search capabilities
- Q&A pair management
- Bulk data operations

---

## 🛠️ Setup Scripts
### Primary Setup Scripts
`setup_complete_system.sh`

Purpose: Complete system initialization
#### What it does:
- Loads environment variables
- Sets up TiDB knowledge base from CSV
- Downloads and configures MCP server binary
- Downloads and configures Llama-Nexus
- Creates all necessary start scripts
- Configures service connections

`start_system.sh`

Purpose: Orchestrated service startup
#### Service startup order:
1. gaia-agentic-search MCP Server (port 9096)
2. Llama-Nexus (port 9095)
3. API Registration
4. FastAPI Application (port 8000)

### Component-Specific Scripts

`setup_mcp_server.sh`
- Downloads gaia-mcp-servers binary
- Platform-specific installation (Linux/macOS, x86_64/ARM64)
- Creates TiDB MCP server configuration

`start_tidb_mcp.sh`:  gaia-agentic-search-mcp tool
#### TiDB MCP Server Configuration:
- Socket: 127.0.0.1:9096
- Table: kubernetes_qa_pairs
- Search tools: Full-text search capabilities

`start_llama_nexus.sh`
- Starts Llama-Nexus gateway on port 9095
- Uses config.toml for MCP server routing
- Provides unified API endpoint

`register_apis.sh`
#### Registers with Llama-Nexus:
- Chat API server (Gaia domains)
- Embedding API server
- Health check verification

### Feature Installation Scripts

`install_voice_features.sh` : Install voice dependencies
#### Dependencies:
- openai-whisper
- torch & torchaudio
- ffmpeg-python
- python-multipart
- System ffmpeg installation

`install_tts_features.sh` : Install tts dependencies
#### Dependencies:
- gtts (Google Text-to-Speech)
- pydub (Audio processing)
---
## Getting Started with the project

1. Clone the repository: 
```
git clone https://github.com/ItshMoh/Exam-BOT.git
```

2. Install dependencies: 
```
pip install -r requirements.txt
```

3. Run the setup script: It will download the LLama-Nexus binary and configure the system.
```
bash setup_complete_system.sh
```
4. Edit the `config.toml file in the nexus folder  to specify a port (9095) for the gateway server to listen to.
```
[server]
host = "0.0.0.0" # The host to listen on.
port = 9095        # The port to listen on.
```
Register the MCP server in this way by adding the below code in the config.toml file in the nexus folder.
```
[[mcp.server.tool]]
name      = "cardea-ExamBot-search"
transport = "stream-http"
url       = "http://127.0.0.1:9096/mcp"
enable    = true
```

5. Start the MCP server: 
```
python3 main.py
```

6. Start the Llama-Nexus gateway: 
```
bash start_system.sh
```

7. Register APIs with Llama-Nexus:
```
bash register_apis.sh
```

8. Run the FastAPI application: 
```
python3 app_nexus.py
```

## ✨ Features

### Core Workflows

#### 📌 Workflow 1: Question Search
1. User asks a specific question.
2. LLM invokes the `get_question_and_answer()` MCP function.
3. The system searches the Qdrant vector database for relevant Q&A pairs.
4. The LLM provides a contextual, helpful response based on the findings.

#### 🎯 Workflow 2: Practice Mode
1. User requests a practice question.
2. LLM invokes the `get_random_question()` MCP function.
3. The system returns a random Q&A pair.
4. The LLM presents the question and guides the user's learning.

---

## 🛠️ Technical Stack

- **Python 3.x**
- **FastMCP** – MCP server framework
- **TiDB** – SQL database for Full text Search
- **SentenceTransformers** – Text embedding generation
- **LLama3** Run the LLAMAEDGE api server locally. 
    
    for running the model that i have used for this project.
    ```bash
    curl -LO https://huggingface.co/tensorblock/Llama-3-Groq-8B-Tool-Use-GGUF/resolve/main/Llama-3-Groq-8B-Tool-Use-Q5_K_M.gguf
   ```
   then run 
   ```bash
   wasmedge --dir .:. --nn-preload default:GGML:AUTO:Llama-3-Groq-8B-Tool-Use-Q5_K_M.gguf \
   llama-api-server.wasm \
   --prompt-template groq-llama3-tool  --log-all \
   --ctx-size 2048 \
   --model-name llama3
   ```

  
- **JSON** – Data storage format

---
## 📁 Project Structure
```

    Directory structure:
└── Exam-BOT
    ├── README.md
    ├── app.py
    ├── app_nexus.py
    ├── install_tts_features.sh
    ├── install_voice_features.sh
    ├── llm.py
    ├── llm_api.py
    ├── llm_api_nexus.py
    ├── main.py
    ├── register_apis.sh
    ├── requirements.txt
    ├── rust_qa.txt
    ├── setup_complete_system.sh
    ├── setup_mcp_server.sh
    ├── start_llama_nexus.sh
    ├── start_system.sh
    ├── start_tidb_mcp.sh
    ├── audio_processing/
    │   ├── audio_utils.py
    │   ├── tts_handler.py
    │   └── whisper_handler.py
    ├── database/
    │   ├── csv_loader.py
    │   ├── dataloader.py
    │   ├── monogodb.py
    │   └── tidb.py
    ├── dataset/
    │   ├── dataPrep.py
    │   ├── file.json
    │   ├── kubernetes_basic.json
    │   ├── kubernetes_qa.csv
    │   ├── mining_qa_pairs.csv
    │   ├── playwright_scrap.py
    │   ├── url_data_fit.py
    │   └── url_scrap.py
    ├── encoder/
    │   └── encoder.py
    ├── static/
    │   ├── audio_recorder.js
    │   ├── index.html
    │   ├── script.js
    │   ├── styles.css
    │   └── uploads/
    │       └── .gitkeep
    ├── utils/
    │   ├── data.py
    │   └── ques_select.py
    └── vectorstore/
        └── qdrant.py

   
```
---
## 🚀 Setup Instructions
### Prerequisites
- Python Dependencies
```bash
pip install -r requirements.txt
```
- Upload the Data on Tidb Cloud. You have to connect to the tiDB instance and save the required login details in the `.env` file.
```bash
python3 database/dataloader.py
```
- Environment Variables Create a .env file:
```bash
OPENAI_API_KEY = "" # you can keep it empty
```
- Setup a MongoDB instance. Make a database and a collection. In the .env variable add the `MONGODB_URI` as a variable and its value.

- Run the app.py file 
```bash
python app.py
```


## 🔧 MCP Functions

### `get_random_question()`
- **Purpose**: Returns a random Q&A pair from the dataset  
- **Use Case**: Practice mode – presents questions for self-testing  
- **Returns**: `dict` with `question` and `answer`

---

### `get_question_and_answer(question: str)`
- **Purpose**: Searches for relevant Q&A pairs using semantic similarity  
- **Use Case**: Query mode – finds answers to specific questions  
- **Returns**: `list` of top 3 matching Q&A pairs with similarity scores

## 🔮 Future Enhancements

 
- **Expanded Datasets**: Add more LF certification topics  
- **Advanced Analytics**: Track learning progress and weak areas  
- **Multi-modal Support**: Include diagrams and visual aids  

---

## 🤝 Contributing

1. Fork the repository  
2. Create your feature branch:  
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. Add your Q&A datasets in the specified format
4. Test your changes with the MCP server
5. Submit a pull request.
---

