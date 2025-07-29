# 🧠 ExamPrepAgent

An AI agent that assists students preparing for any exam or test, such as **Linux Foundation (LF) certifications**. The agent serves as an intelligent study companion leveraging **Large Language Models (LLMs)** and **MCP servers** to provide an engaging and interactive learning experience. The agent supports:

- Ask random study questions
- Semantic and keyword search of the correct answers
- Guided conversation for deeper understanding

It consists of two major components.

* An MCP (Model Context Protocol) server that provides tools to search for study questions and answers from a knowledge base. It can be used with any MCP-compatible LLM client.
* A chatbot application that utilizes any LLM and the MCP server. It asks the user study questions, and helps the user to reach the correct answer.

---

Here is the demo video of bot in action: 
https://www.loom.com/share/e11263ab6c3e4a4da33e5e2b726cfd80?sid=173cf35a-8447-4666-b374-a78f5c5193d4

---

## 🚀 Getting Started

1. Clone the repository.

```
https://github.com/cardea-mcp/ExamPrepAgent.git
```

2. Install dependencies

```
pip install fastmcp fastapi requests mysql-connector-python ffmpeg
```

3. Create a `.env` file from the `.env.example` file and fill in the required values.

You will need API endpoints for an LLM service, and the system prompt for the conversation management. If you want to use the voice features on the chatbot app, you will also need API endpoints for ASR and TTS services. You can run LLM, ASR, and TTS services [using open-source models locally on your own computers via LlamaEdge](https://llamaedge.com/docs/ai-models/). 

6. Set up the question and answer database.


```
bash setup_dataset.sh
```

5. Start the MCP server.

```
python3 main.py
```

6. Start the chatbot app.

```
python3 app.py
```

---

ScreenShots of the bot in action
![Bot giving practicing question to the user](public/lfx_exambot_ui_sc.png)

---

We have created two datasets for the QA knowledge base for you to experiment with. The Kubernetes QA is the default dataset used in our scripts.

- **Kubernetes-Q&A** - A collection of Q&A pairs focused on Kubernetes and cloud native concepts. It is uploaded to my hugging face id. 
here is the link to the dataset. https://huggingface.co/datasets/ItshMoh/kubernetes_qa_pairs . It contains 497 Q&A pairs. It has also crossed **45 downloads** on hugging face.
It is made for KCNA exam. Contents are taken from the kubernetes.io licensed under CC BY 4.0

- **Metal-mining-Q&A** - A collection of Q&A pairs focused on metal mining methods. The link to the dataset https://huggingface.co/datasets/ItshMoh/metal-mining-qa-pairs . It has also more than 31 downloads on hugging face.

## 🏗️ Architecture

### 🔧 Key Files Description

#### Core Application Files

`app.py`

`app.py`: Direct API integration architecture

- Communicates directly with LLM APIs (OpenAI-compatible)
- Manages MCP server subprocess internally
- Suitable for direct API deployments


#### LLM Integration Files


`llm_api.py` - FastAPI Integration (Direct)

- HTTP API endpoint integration
- Subprocess MCP server management
- Audio message processing
- Session-based context handling



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

## ✨ Features

### Core Workflows

#### 📌 Workflow 1: Question Search
1. User asks a specific question.
2. LLM invokes the `get_question_and_answer()` MCP function.
3. The system searches the TiDB for relevant Q&A pairs.
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
- **JSON** – Data storage format

---
## 📁 Project Structure
```

└── ExamPrepAgent/
    ├── README.md
    ├── app.py
    ├── llm_api.py
    ├── llmclient.py
    ├── load_dataset.py
    ├── main.py
    ├── requirements.txt
    ├── setup_dataset.sh
    ├── url_scrap.py
    ├── .env.example
    ├── audio_processing/
    │   ├── audio_utils.py
    │   ├── tts_handler.py
    │   └── whisper_handler.py
    ├── database/
    │   ├── csv_loader.py
    │   ├── dataloader.py
    │   └── tidb.py
    ├── dataset/
    │   ├── csv_loader.py
    │   ├── dataPrep.py
    │   ├── file.json
    │   ├── kubernetes_basic.json
    │   ├── playwright_scrap.py
    │   ├── url_data_fit.py
    │   └── url_scrap.py
    ├── static/
    │   ├── audio_recorder.js
    │   ├── index.html
    │   ├── script.js
    │   ├── styles.css
    │   └── uploads/
    │       └── .gitkeep
    └── utils/
        └── ques_select.py

   
```
---

## 🔮 Future Enhancements

- **Expanded Datasets**: Add more LF certification topics  
- **Advanced Analytics**: Track learning progress and weak areas  
- **Multi-modal Support**: Include diagrams and visual aids  
---

### Kubernetes Dataset

The dataset has been created using the [kubernetes.io](https://kubernetes.io) documentation. It is available under CC BY 4.0. license. 

Here is the link to the [dataset](https://huggingface.co/datasets/ItshMoh/kubernetes_qa_pairs)

The dataset has been generated using this [script](https://github.com/cardea-mcp/ExamPrepAgent/blob/master/url_scrap.py)

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

