# 🧠 MCP-Based AI Agent for LF Certificate Prep

A prototype AI agent built using the **Model Context Protocol (MCP)** to assist students preparing for **Linux Foundation (LF) certifications** through interactive practice questions and intelligent Q&A responses.

---

## 🚀 Project Overview

This project serves as an intelligent study companion leveraging **open-source Large Language Models (LLMs)** and **MCP servers** to provide an engaging and interactive learning experience. The agent supports:

- Random practice questions
- Semantic search of relevant Q&A pairs
- Guided conversation for deeper understanding

---

## 🏗️ Architecture

The system is composed of several core components:

- **MCP Server (`main.py`)**  
  Handles question retrieval via defined MCP functions.

- **Vector Database (Qdrant)**  
  Stores text embeddings for efficient semantic search.

- **LLM Integration (`llm.py`)**  
  Interfaces with OpenAI-compatible APIs to manage conversation flow.

- **Question Database**  
  A collection of text-based Q&A pairs focused on mining and technical certification topics.

---

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
- **Qdrant** – Vector database for semantic search
- **SentenceTransformers** – Text embedding generation
- **OpenAI API** (via gaianet node)
- **JSON** – Data storage format

---
## 📁 Project Structure
```
├── main.py              # MCP server with tool definitions
├── llm.py               # LLM integration and chat loop
├── data.py              # Data loading from text files
├── encoder.py           # Text embedding creation
├── qdrant.py            # Vector database setup and indexing
├── ques_select.py       # Question selection and search functions
├── file.json            # Sample Q&A dataset
└── README.md           
```
---
## 🚀 Setup Instructions
### Prerequisites
- Qdrant VectorStore
```bash
docker run -p 6333:6333 qdrant/qdrant
```
- Python Dependencies
```bash
pip install -r requirements.txt
```
- Environment Variables Create a .env file:
```bash
OPENAI_API_KEY = "" # you can keep it empty
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

- **WasmEdge Integration**: Migrate to CNCF WasmEdge runtime  
- **LlamaEdge Framework**: Implement agent using LlamaEdge  
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
5. Submit a pull request
---
## 📝 License
This project is part of the Linux Foundation certification preparation initiative.
Please ensure compliance with LF guidelines when using certification materials.
