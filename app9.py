from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
import PyPDF2
import docx
import io

# Load environment variables
load_dotenv()
os.environ["GROQ_API_KEY"] = ""
os.environ["TAVILY_API_KEY"] = ""

app = FastAPI(title="Research Chatbot API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Groq LLM
llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.5
)

# Pydantic models for request validation
class TextQuery(BaseModel):
    query: str

class VoiceQuery(BaseModel):
    voice_text: str
    prompt: str

# Document processing functions
async def extract_pdf_text(file: bytes) -> str:
    pdf_file = io.BytesIO(file)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

async def extract_docx_text(file: bytes) -> str:
    docx_file = io.BytesIO(file)
    doc = docx.Document(docx_file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def process_query(query: str, context: str = "") -> str:
    if context:
        full_query = f"{query}\n\nAdditional Context:\n{context}"
    else:
        full_query = query

    # Optimize query
    prompt = f'''Modify this query for internet search to find research-focused results: "{full_query}"
    Return only the optimized search query without any additional text.'''
    optimized_query = llm.invoke(prompt).content

    # Search
    search = TavilySearchResults(max_results=2, search_depth="advanced")
    results = search.invoke(optimized_query)

    # Generate report
    sources = "\n".join([f"Source {i+1}: {result['url']}\nContent: {result['content']}\n"
                        for i, result in enumerate(results)])
    
    report_prompt = f'''Generate a detailed research report based on the following sources:

    {sources}

    Format the report as follows:
    1. Executive Summary
    2. Key Findings
    3. Detailed Analysis
    4. Trends and Insights
    5. Citations

    Ensure all information is properly cited using [Source X] format.'''

    response = llm.invoke(report_prompt).content
    return response

# 1. Text-only endpoint
@app.post("/api/text")
async def text_only_endpoint(query: TextQuery):
    """
    Process text-only queries
    """
    try:
        response = process_query(query.query)
        return {
            "status": "success",
            "response": response
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )

# 2. Document upload with prompt endpoint
@app.post("/api/document")
async def document_with_prompt(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    description: Optional[str] = Form(None)
):
    """
    Process document upload with prompt
    """
    try:
        if not file.filename.endswith(('.pdf', '.docx')):
            return JSONResponse(
                status_code=415,
                content={
                    "status": "error",
                    "message": "Only PDF and DOCX files are supported"
                }
            )

        contents = await file.read()
        
        if file.filename.endswith('.pdf'):
            text = await extract_pdf_text(contents)
        else:
            text = await extract_docx_text(contents)

        response = process_query(prompt, text)
        
        return {
            "status": "success",
            "filename": file.filename,
            "prompt": prompt,
            "description": description,
            "response": response
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )

# 3. Voice input with prompt endpoint
@app.post("/api/voice")
async def voice_with_prompt_endpoint(query: VoiceQuery):
    """
    Process voice input with prompt
    """
    try:
        combined_query = f"{query.prompt}\nVoice Input: {query.voice_text}"
        response = process_query(combined_query)
        
        return {
            "status": "success",
            "voice_text": query.voice_text,
            "prompt": query.prompt,
            "response": response
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)