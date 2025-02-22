from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import PyPDF2
import docx
import io

app = FastAPI()

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

@app.post("/upload/document")
async def upload_document(
    file: UploadFile = File(...),
    description: str = Form(...)  # Added form field
):
    if not (file.filename.endswith('.pdf') or file.filename.endswith('.docx')):
        return JSONResponse(
            status_code=400,
            content={"message": "Only PDF and DOCX files are allowed"}
        )
    
    try:
        contents = await file.read()
        
        # Print the input field value
        print(f"\nDescription provided: {description}")
        
        if file.filename.endswith('.pdf'):
            text = await extract_pdf_text(contents)
            file_type = "PDF"
        else:
            text = await extract_docx_text(contents)
            file_type = "DOCX"
            
        print(f"\nExtracted text from {file_type} {file.filename}:")
        print(text)
        
        return {
            "message": f"{file_type} processed successfully",
            "filename": file.filename,
            "description": description,
            "text": text
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Error processing file: {str(e)}"}
        )