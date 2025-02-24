

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from pydub import AudioSegment
import shutil
from langchain_community.tools.tavily_search import TavilySearchResults

FFMPEG_INSTALLED = shutil.which('ffmpeg') is not None
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
import PyPDF2
import docx
import io
import speech_recognition as sr
import tempfile
import wave



load_dotenv()
os.environ["GROQ_API_KEY"] = ""
os.environ["TAVILY_API_KEY"] = ""

app = FastAPI(title="Research API")

llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.5
)

class Query(BaseModel):
    text: str

def user_query_optimize_node(input_text):
    """Optimizes user query for search"""
    prompt = f'''Modify this query for internet search to find research-focused results: "{input_text}"
    Return only the optimized search query without any additional text.'''
    return llm.invoke(prompt).content

def search_node(input_text: str) :
    """Performs search using Tavily"""
    search = TavilySearchResults(max_results=2, search_depth="advanced")
    return search.invoke(input_text)

def final_node(search_results,user_prompt=None):
    """Generates research report"""
    print("up=====",user_prompt)
    sources = "\n".join([f"Source {i+1}: {result['url']}\nContent: {result['content']}\n"
                        for i, result in enumerate(search_results)])
    print("\n\nsource=======> ",sources)
    
    prompt = f'''Generate a detailed research report based on the following sources:
{sources}
    Here is user query="{user_prompt}" and Here is sources="{sources}"
based on user query and source give a report .
Format the report as follows:
1. Executive Summary
2. Key Findings
3. Detailed Analysis
4. Trends and Insights
5. Citations

Ensure all information is properly cited using [Source X] format.'''

    return llm.invoke(prompt).content



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

async def process_audio_file(audio_file: bytes, filename: str) -> str:
    """
    Process audio file and convert to text using speech recognition
    Supports both WAV and MP3 formats
    """
    recognizer = sr.Recognizer()
    temp_files = []
    
    try:
        is_mp3 = filename.lower().endswith('.mp3')
        if is_mp3 and not FFMPEG_INSTALLED:
            raise HTTPException(
                status_code=500,
                detail="FFmpeg is not installed. Please install FFmpeg to process MP3 files."
            )
        

        if is_mp3:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_mp3:
                    temp_mp3.write(audio_file)
                    temp_mp3_path = temp_mp3.name
                    temp_files.append(temp_mp3_path)
                
                # Convert MP3 to WAV
                audio = AudioSegment.from_mp3(temp_mp3_path)
                temp_audio_path = temp_mp3_path[:-4] + '.wav'
                audio.export(temp_audio_path, format='wav')
                temp_files.append(temp_audio_path)
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing MP3 file: {str(e)}. Please ensure FFmpeg is properly installed."
                )
        else:
            # For WAV files, use directly
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
                temp_audio.write(audio_file)
                temp_audio_path = temp_audio.name
                temp_files.append(temp_audio_path)
        
        # Process the audio file
        try:
            with sr.AudioFile(temp_audio_path) as source:
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.record(source)
                text = recognizer.recognize_google(audio)
                return text
        except sr.UnknownValueError:
            raise HTTPException(status_code=400, detail="Could not understand audio")
        except sr.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Speech recognition API request failed: {str(e)}")
        
    finally:
        # Clean up all temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception:
                pass
    
    try:
        # Load the audio file
        with sr.AudioFile(temp_audio_path) as source:
            # Adjust for ambient noise and record
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.record(source)
            
            # Convert speech to text
            text = recognizer.recognize_google(audio)
            return text
            
    except sr.UnknownValueError:
        raise HTTPException(status_code=400, detail="Could not understand audio")
    except sr.RequestError as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")
    finally:
        # Clean up all temporary files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except Exception:
                pass


@app.post("/only_text")
async def process_query(query: Query):
    try:
        # Process through the workflow
        optimized_query = user_query_optimize_node(query.text)
        print(f"optimized_qurey============> {optimized_query}")
        search_results = search_node(optimized_query)
        print(f"search result============> {search_results}")
        final_report = final_node(search_results)
        print(f"final report============> {final_report}")
        
        return {"result": final_report}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@app.post("/api/document")
async def document_with_prompt(
    file: UploadFile = File(...),
    prompt: str = Form(...)
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
        xx=""
        
        if file.filename.endswith('.pdf'):
            text = await extract_pdf_text(contents)
            xx=text
            print(';;;;;;;;;;;;;;;;;; ======= > ',text)
        else:
            text = await extract_docx_text(contents)

        # response = process_query(prompt, text)

        optimized_query = user_query_optimize_node(prompt)
        print(f"optimized_qurey============> {optimized_query}")
        search_results = search_node(optimized_query)
        print(f"search result============> {search_results}")
        final_report = final_node(search_results,prompt)
        print(f"final report============> {final_report}")
        
        return {
            "status": "success",
            "filename": file.filename,
            "prompt": prompt,
            "text": xx
            # "response": response
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )
    




@app.post("/api/voice-to-text")
async def voice_to_text(
    audio_file: UploadFile = File(...),
):
    """
    Convert voice recording to text
    Accepts .wav audio files
    """
    try:
        if not audio_file.filename.lower().endswith(('.wav', '.mp3')):
            return JSONResponse(
                status_code=415,
                content={
                    "status": "error",
                    "message": "Only WAV and MP3 audio files are supported"
                }
            )

        # Read the audio file
        contents = await audio_file.read()
        
        # Process the audio and get text
        transcribed_text = await process_audio_file(contents, audio_file.filename)
        
        return {
            "status": "success",
            "filename": audio_file.filename,
            "transcribed_text": transcribed_text
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
