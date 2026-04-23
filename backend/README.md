cd backend

pip install fastapi uvicorn python-dotenv groq langgraph sqlalchemy psycopg2-binary

.env:
GROQ_API_KEY=your_api_key_here

CREATE DATABASE crm;

replace :
DATABASE_URL = "postgresql://langgraph:sreehari30@localhost:5432/crm"

run
uvicorn main:app --reload
