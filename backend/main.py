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

from sqlalchemy import create_engine, Column, String, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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
# DATABASE
# =============================
DATABASE_URL = "postgresql://postgres:sreehari30@localhost:5432/langgraph"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True)
    hcp_name = Column(String)
    attendees = Column(Text)
    topics = Column(Text)
    sentiment = Column(String)
    outcomes = Column(Text)
    follow_up = Column(Text)
    summary = Column(Text)
    materials_shared = Column(Text)
    samples = Column(Text)
    date = Column(String)
    time = Column(String)

Base.metadata.create_all(bind=engine)

def save_to_db(data):
    db = SessionLocal()

    interaction = Interaction(
        hcp_name=data.get("hcp_name"),
        attendees=", ".join(data.get("attendees", [])),
        topics=data.get("topics"),
        sentiment=data.get("sentiment"),
        outcomes=data.get("outcomes"),
        follow_up=data.get("follow_up"),
        summary=data.get("summary"),
        materials_shared=", ".join(data.get("materials_shared", [])),
        samples=", ".join(data.get("samples", [])),
        date=data.get("date"),
        time=data.get("time"),
    )

    db.add(interaction)
    db.commit()
    db.close()

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
# RULE BASED EXTRACTION
# =============================

def extract_hcp(text):
    text = text.lower()

    dr = re.search(r"dr\.?\s*[a-z]+", text)
    if dr:
        return dr.group().title()

    match = re.search(r"(met|visited|consulted)\s+([a-z]+)", text)
    if match:
        return match.group(2).title()

    return None


def extract_attendees(text, hcp):
    text = text.lower()

    attendees = []

    # CASE 1: "with ..."
    match = re.search(r"with\s+(.+)", text)
    if match:
        names = re.split(r",|and", match.group(1))
        attendees += [n.strip().title() for n in names if n.strip()]

    # CASE 2: first word before "met"
    first = re.match(r"([a-z]+)\s+(met|meet|visited)", text)
    if first:
        name = first.group(1).title()
        if hcp and name.lower() not in hcp.lower():
            attendees.append(name)

    return list(set(attendees))


def extract_datetime(text, data):
    # 4-digit year
    match1 = re.search(r"\d{2}/\d{2}/\d{4}", text)
    # 2-digit year
    match2 = re.search(r"\d{2}/\d{2}/\d{2}", text)

    if match1:
        data["date"] = match1.group()
    elif match2:
        data["date"] = match2.group()

    time = re.search(r"\d{1,2}[:.]\d{2}\s?(am|pm)?", text.lower())
    if time:
        data["time"] = time.group()

    return data


def classify_resources(text, data):
    text = text.lower()

    materials = []
    samples = []

    if "report" in text or "xray" in text or "brochure" in text:
        materials.append("Report")

    if "medicine" in text or "tablet" in text or "sample" in text:
        samples.append("Medicine")

    data["materials_shared"] = list(set(data.get("materials_shared", []) + materials))
    data["samples"] = list(set(data.get("samples", []) + samples))

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
# TOOLS
# =============================

def log_tool(data):
    global GLOBAL_FORM

    for key, value in data.items():

        # 🟢 HANDLE LIST FIELDS
        if key in ["attendees", "materials_shared", "samples"]:
            existing = GLOBAL_FORM.get(key, [])

            if not isinstance(existing, list):
                existing = []

            if isinstance(value, list):
                GLOBAL_FORM[key] = list(set(existing + value))

        # 🟡 HANDLE STRING FIELDS
        else:
            if value:
                GLOBAL_FORM[key] = value

    # 🔥 sentiment
    GLOBAL_FORM["sentiment"] = call_llm(f"""
Return ONLY one word:
positive OR neutral OR negative

Text:
{GLOBAL_FORM}
""").strip().lower()

    return {"status": "logged"}


def edit_tool(data):
    global GLOBAL_FORM

    for key, value in data.items():
        if not value:
            continue

        if key in ["attendees", "materials_shared", "samples"]:
            GLOBAL_FORM[key] = value if isinstance(value, list) else [value]
        else:
            GLOBAL_FORM[key] = value

    return {"status": "edited"}

def summarize_tool():
    global GLOBAL_FORM

    GLOBAL_FORM["summary"] = call_llm(f"""
Write 2 line professional medical CRM summary.
No symbols. No markdown.

Data:
{GLOBAL_FORM}
""").strip()

    return {"status": "summarized"}


def followup_tool():
    global GLOBAL_FORM

    GLOBAL_FORM["follow_up"] = call_llm(f"""
Give 3 professional doctor follow-up actions.
No symbols. Plain text.

Context:
{GLOBAL_FORM}
""")

    return {"status": "followup"}

# =============================
# LANGGRAPH
# =============================

def decide_tool(state):
    text = state["input"].lower()

    if "summary" in text:
        state["tool"] = "summarize"
    elif "follow" in text:
        state["tool"] = "followup"
    elif "edit" in text or "change" in text:
        state["tool"] = "edit"
    else:
        state["tool"] = "log"

    return state


def extract_node(state):
    text = state["input"]

    # LLM only for topics/outcomes
    result = call_llm(f"""
Extract ONLY:
topics, outcomes

Return JSON.

Text:
{text}
""")

    try:
        data = json.loads(result[result.find("{"):result.rfind("}")+1])
    except:
        data = {}

    # RULE BASED (MAIN FIX)
    hcp = extract_hcp(text)
    if hcp:
        data["hcp_name"] = hcp

    data["attendees"] = extract_attendees(text, data.get("hcp_name"))

    data = extract_datetime(text, data)
    data = classify_resources(text, data)

    state["data"] = data
    return state


def tool_node(state):
    tool = state["tool"]
    data = state.get("data", {})

    if tool == "log":
        return log_tool(data)
    elif tool == "edit":
        return edit_tool(data)
    elif tool == "summarize":
        return summarize_tool()
    elif tool == "followup":
        return followup_tool()

    return {"status": "no_action"}


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
    return {"form_data": GLOBAL_FORM, "message": result["status"]}


@app.post("/save")
async def save():
    save_to_db(GLOBAL_FORM)
    return {"message": "Saved to DB"}


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
        app_graph.invoke({"input": text})

        return {"form_data": GLOBAL_FORM, "message": "Voice processed"}

    finally:
        os.remove(path)