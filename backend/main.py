import os
import json
import re
import tempfile

from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

from langgraph.graph import StateGraph
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

# =============================
# CORS
# =============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================
# GROQ
# =============================
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# =============================
# GLOBAL STATE
# =============================
GLOBAL_FORM = {
    "hcp_name": "",
    "attendees": [],
    "topics": "",
    "sentiment": "",
    "outcomes": "",
    "follow_up": "",
    "materials_shared": [],
    "samples": [],
    "date": "",
    "time": "",
    "summary": ""
}

class ChatRequest(BaseModel):
    message: str

# =============================
# UTIL FUNCTIONS
# =============================

def normalize_attendees(data):
    attendees = data.get("attendees")

    if isinstance(attendees, str):
        attendees = re.split(r"\band\b|,", attendees)

    if isinstance(attendees, list):
        cleaned = []
        for person in attendees:
            person = person.strip()
            if person.lower() == "me":
                cleaned.append("Self")
            else:
                cleaned.append(person.title())

        data["attendees"] = cleaned

    return data


def normalize_list(value):
    if isinstance(value, str):
        return [v.strip() for v in value.split(",")]
    return value if isinstance(value, list) else []


def extract_datetime(text, data):
    date_match = re.search(r"\b\d{2}-\d{2}-\d{4}\b", text)
    if date_match:
        data["date"] = date_match.group()

    time_match = re.search(r"\b\d{1,2}[:.]\d{2}\s?(am|pm)?\b", text.lower())
    if time_match:
        data["time"] = time_match.group()

    return data


# =============================
# LLM
# =============================

def call_llm(prompt):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content


# =============================
# TOOL FUNCTIONS
# =============================

def log_tool(data):
    global GLOBAL_FORM

    for key, value in data.items():

        if key in ["materials_shared", "samples"]:
            if isinstance(value, list):
                existing = GLOBAL_FORM.get(key, [])
                GLOBAL_FORM[key] = list(set(existing + value))
        else:
            if value not in ["", [], None]:
                GLOBAL_FORM[key] = value

    # 🔥 AUTO AI INSIGHTS

    GLOBAL_FORM["sentiment"] = call_llm(
        f"Classify sentiment (positive, neutral, negative):\n{GLOBAL_FORM}"
    )

    #GLOBAL_FORM["follow_up"] = call_llm(
        #f"Suggest professional follow-up actions for this doctor interaction:\n{GLOBAL_FORM}"
    #)

    #GLOBAL_FORM["summary"] = call_llm(
       # f"Write a clear professional summary of this healthcare interaction:\n{GLOBAL_FORM}"
    #)

    return {"status": "logged", "form_data": GLOBAL_FORM}


def edit_tool(data):
    global GLOBAL_FORM

    for key, value in data.items():

        if key in ["materials_shared", "samples"]:
            if isinstance(value, list):
                existing = GLOBAL_FORM.get(key, [])
                GLOBAL_FORM[key] = list(set(existing + value))
        else:
            if value not in ["", [], None]:
                GLOBAL_FORM[key] = value

    return {"status": "edited", "form_data": GLOBAL_FORM}


def summarize_tool():
    global GLOBAL_FORM

    GLOBAL_FORM["summary"] = call_llm(
        f"Write a professional summary of this interaction make it short and understanble to anyone Rules: -plain text only -no formating ,- no ** symbols make it proffessional Text:{GLOBAL_FORM}"
    )

    return {"status": "summarized", "form_data": GLOBAL_FORM}


def sentiment_tool(text):
    global GLOBAL_FORM

    GLOBAL_FORM["sentiment"] = call_llm(
        f"Classify sentiment of this interaction. Return ONLY one word:positive OR neutral OR negative no explanation : Text: {GLOBAL_FORM}"
    ).strip().lower()

    return {"status": "sentiment_updated", "form_data": GLOBAL_FORM}


def followup_tool():
    global GLOBAL_FORM

    GLOBAL_FORM["follow_up"] = call_llm(
        f"Suggest next steps for this interaction like short 3-4 proffesional follow-up action relevent Rules:-Bullet points only, -No explanation - no symbols like ** Text:{GLOBAL_FORM}"
    )

    return {"status": "followup_generated", "form_data": GLOBAL_FORM}


# =============================
# LANGGRAPH NODES
# =============================

def decide_tool(state):
    text = state["input"]

    prompt = f"""
You are an AI assistant for a Healthcare CRM.

Choose ONE tool:

- log
- edit
- summarize
- sentiment
- followup

You are an AI assistant for a Healthcare CRM system.

Your task is to choose ONE tool based on the user's input.

Available tools:
- log → when user describes a meeting or interaction
- edit → when user modifies existing data
- summarize → when user asks for summary
- sentiment → when user expresses opinion/emotion
- followup → when user asks next steps

Guidelines:
- Mentions of doctors, meetings, medicines → log
- Updates like "change", "update" → edit
- "summarize" → summarize
- emotional tone → sentiment
- "next step" → followup

Return ONLY one word from:
log, edit, summarize, sentiment, followup

Rules:
- Meeting/doctor/medicine → log
- change/update → edit
- summary request → summarize
- emotional tone → sentiment
- next steps → followup
- Medicines → samples
- Documents → materials_shared
- Return ONLY valid JSON
- If not present → leave empty

Text:
{text}

Return ONE word only.
"""

    tool = call_llm(prompt).strip().lower()

    # ✅ Safety mapping
    if "log" in tool:
        tool = "log"
    elif "edit" in tool:
        tool = "edit"
    elif "summar" in tool:
        tool = "summarize"
    elif "sentiment" in tool:
        tool = "sentiment"
    elif "follow" in tool:
        tool = "followup"
    else:
        tool = "log"

    state["tool"] = tool
    return state


def extract_node(state):
    text = state["input"]

    prompt = f"""
Extract structured CRM data.

Return ONLY JSON.

Fields:
hcp_name, attendees, topics, sentiment, outcomes, follow_up,
materials_shared, samples

You are an AI system extracting structured medical CRM interaction data.

Extract the following fields from the text:

- hcp_name (doctor name)
- attendees (list of people)
- topics (discussion topics)
- sentiment (positive, neutral, negative)
- outcomes
- follow_up
- materials_shared (documents like brochure, report, pdf)
- samples (medicines/products)

Rules:
- Medicines → samples
- Documents → materials_shared
- Medicines → samples
- Documents → materials_shared
- Return ONLY valid JSON
- If not present → leave empty


Text:
{text}
"""

    result = call_llm(prompt)

    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        data = json.loads(result[start:end])
    except:
        data = {}

    data = normalize_attendees(data)
    data["materials_shared"] = normalize_list(data.get("materials_shared"))
    data["samples"] = normalize_list(data.get("samples"))
    data = extract_datetime(text, data)

    state["data"] = data
    return state


def tool_node(state):
    tool = state.get("tool")
    data = state.get("data", {})
    text = state.get("input")

    if tool == "log":
        return log_tool(data)

    elif tool == "edit":
        return edit_tool(data)

    elif tool == "summarize":
        return summarize_tool()

    elif tool == "sentiment":
        return sentiment_tool(text)

    elif tool == "followup":
        return followup_tool()

    return {"status": "no_action"}


# =============================
# GRAPH
# =============================

graph = StateGraph(dict)

graph.add_node("decide", decide_tool)
graph.add_node("extract", extract_node)
graph.add_node("tool", tool_node)

graph.set_entry_point("decide")
graph.add_edge("decide", "extract")
graph.add_edge("extract", "tool")

app_graph = graph.compile()


# =============================
# API
# =============================

@app.post("/chat")
async def chat(req: ChatRequest):
    result = app_graph.invoke({"input": req.message})

    return {
        "form_data": GLOBAL_FORM,
        "message": result.get("status", "done")
    }


@app.post("/voice")
async def voice(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        tmp.write(await file.read())
        path = tmp.name

    try:
        with open(path, "rb") as audio:
            transcription = client.audio.transcriptions.create(
                file=audio,
                model="whisper-large-v3"
            )

        text = transcription.text

        result = app_graph.invoke({"input": text})

        return {
            "form_data": GLOBAL_FORM,
            "message": f"Voice processed"
        }

    finally:
        os.remove(path)