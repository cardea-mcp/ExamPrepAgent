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

The system is composed of several core components:

- **MCP Server (`main.py`)**  
  Handles question retrieval via defined MCP functions.

- **TiDB **  
  It stores the required Dataset of Q&A pairs. It is like SQL with Full text search feature. You can read about it here. https://docs.pingcap.com/tidbcloud/vector-search-full-text-search-python/

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

    ├── README.md
    ├── app.py
    ├── llm.py
    ├── llm_api.py
    ├── main.py
    ├── requirements.txt
    ├── rust_qa.txt
    ├── database/
    │   └── monogodb.py
    ├── dataset/
    │   ├── dataPrep.py
    │   ├── file.json
    │   ├── kubernetes_basic.json
    │   ├── kubernetes_qa.csv
    │   ├── mining_qa_pairs.csv
    │   ├── url_data_fit.py
    │   └── url_scrap.py
    ├── encoder/
    │   └── encoder.py
    ├── public/
    ├── static/
    │   ├── index.html
    │   ├── script.js
    │   └── styles.css
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

