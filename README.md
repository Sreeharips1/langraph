# 🧠 AI-First CRM HCP Interaction Module

## 📌 Overview

This project is an AI-powered CRM module designed for logging Healthcare Professional (HCP) interactions. It allows users to log interactions using both structured forms and conversational AI.

The system uses LangGraph with LLMs to intelligently extract, update, and enhance CRM data.

---

## 🚀 Features

- 📝 Dual Input System
  - Structured form input
  - Conversational AI assistant

- 🤖 AI-Powered Extraction
  - Extract HCP name, attendees, topics, date, time
  - Identify materials shared and samples

- ✏️ Edit via Chat
  - Modify existing data using natural language

- 📊 AI Insights
  - Sentiment analysis (positive/neutral/negative)
  - Follow-up action generation
  - Interaction summary

- 🎤 Voice Input
  - Convert speech → text → structured CRM data

- 💾 Database Integration
  - Save interactions to PostgreSQL

---

## 🧠 Tech Stack

### Frontend

- React
- Redux
- CSS (Google Inter Font)

### Backend

- FastAPI (Python)
- LangGraph (AI Agent Framework)
- Groq LLM API (Llama 3.3 70B / Gemma)

### Database

- PostgreSQL

---

## 🧩 LangGraph Agent

The LangGraph agent manages the entire workflow using a decision-based graph:

1. Decide user intent
2. Extract structured data
3. Execute appropriate tool

---

## 🔧 LangGraph Tools (5 Required)

### 1. Log Interaction

- Extracts structured data from user input
- Updates CRM form fields

### 2. Edit Interaction

- Updates existing fields using user instructions
- Example: “Change date to tomorrow”

### 3. Summarize Interaction

- Generates a concise professional summary
- Based on current form data

### 4. Sentiment Analysis

- Classifies tone into:
  - Positive
  - Neutral
  - Negative

### 5. Follow-up Generator

- Suggests professional next steps for field reps

---

## 🧠 Architecture

User Input → LangGraph Agent → Tool Selection → Data Processing → UI Update → Optional DB Save

---

## ⚙️ Setup Instructions

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
