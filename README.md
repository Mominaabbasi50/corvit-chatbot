# Corvit Chatbot

An **AI-powered chatbot** developed as a **Final Year Project** at Corvit Systems.  
This chatbot provides **student support, event information, FAQs, and course-related guidance**, with a clean **Streamlit interface** and an intelligent retriever-based backend.

## Overview

The Corvit Chatbot is designed to:

- Help students interact with the institute through natural conversations
- Answer FAQs about courses, admissions, and schedules
- Provide upcoming events and reminders
- Support multi-language input (English + Urdu)
- Manage chat history for each user
- Suggest common questions for faster help

---

## Features

- **User Authentication** (register/login using SQLite + bcrypt)
- **Conversational Chatbot** with context handling
- **Retrieval-Augmented Generation (RAG)** using FAISS vector search
- **Suggested Q&A** for quick access
- **Event Calendar** showing upcoming 7 days of events
- **Multi-language Support** (Urdu → English translation before processing)
- **Chat History**: save, load, and delete conversations
- **Modern UI** built with Streamlit

---

## Tech Stack

- **Frontend:** Streamlit, CSS, Pillow (for images)
- **Backend:** Python, SQLite (database), LangChain
- **AI/ML:** HuggingFace Transformers, SentenceTransformers, FAISS, PyTorch
- **Security:** bcrypt (password hashing)
- **Integrations:** OpenAI API

---

## Project Structure

- **app.py** → Main Streamlit app
- **auth.py** → User authentication
- **chat_handler.py** → Chatbot response logic
- **model_inference.py** → Model loading & inference
- **preprocess_input.py** → Language detection & translation
- **requirements.txt** → Dependencies
- **.env.example** → Environment template
- **.gitignore** → Ignored files

### utils/ (Helper modules)

- event_utils.py
- chat_utils.py
- history_utils.py
- recommendation_utils.py
- suggested_qna.py

### model/

- Config files (no weights included)

### retriever/

- FAISS retriever config (no index included)

### css/

- Stylesheets

### images/

- Logos / screenshots

### notebooks/

- Colab notebooks (training + retriever build)

## Installation & Setup

### 1. Clone Repository

git clone https://github.com/your-username/corvit-chatbot.git
cd corvit-chatbot

### 2. Create Virtual Environment

python -m venv venv
venv\Scripts\activate # Windows
source venv/bin/activate # Mac/Linux

### 3. Install Dependencies

pip install -r requirements.txt

### 4. Configure Environment

Create .env file in the root folder (copy from .env.example):

OPENAI_API_KEY=your_api_key_here

### 5. Run the Application

streamlit run app.py

## Usage Flow

Register/Login as a user

Start conversation with chatbot

Ask questions about courses, admissions, or events

View upcoming 7-day event schedule

Use suggested Q&A for faster interaction

Save or delete past chats

## How It Works

Preprocessing: Urdu text → English translation, text cleaning

Embeddings: SentenceTransformers to create semantic vectors

Retriever: FAISS index for similarity search

Model: HuggingFace Transformers + OpenAI API for generating responses

Evaluation: Tested on FAQs and student queries

## Future Improvements

Multi-agent design (separate agents for events, FAQs, courses)

Voice-enabled chatbot

Mobile app version

Integration with Corvit’s LMS

## Author

Momina Abbasi — Final Year Project @ Corvit Systems
