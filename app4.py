from fastapi import FastAPI, UploadFile, File, Form, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import PyPDF2
import docx
import io

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Document upload endpoint
@app.post("/upload/document")
async def upload_document(
    file: UploadFile = File(...),
    description: str = Form(...)
):
    if not (file.filename.endswith('.pdf') or file.filename.endswith('.docx')):
        return JSONResponse(
            status_code=400,
            content={"message": "Only PDF and DOCX files are allowed"}
        )
    
    try:
        contents = await file.read()
        
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

# Speech-to-text WebSocket endpoint
@app.websocket("/ws/speech-to-text")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            text = await websocket.receive_text()
            print(f"Received speech text: {text}")
            
            await websocket.send_json({
                "status": "success",
                "text": text
            })
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        await websocket.close()

# HTML page endpoint
@app.get("/", response_class=HTMLResponse)
async def get_html():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Document Processing and Speech-to-Text</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            .section {
                margin-bottom: 40px;
                padding: 20px;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            #result {
                margin-top: 20px;
                padding: 10px;
                border: 1px solid #ccc;
                min-height: 100px;
            }
            button {
                padding: 10px 20px;
                font-size: 16px;
                cursor: pointer;
                margin: 5px;
            }
            .status {
                margin-top: 10px;
                color: #666;
            }
            form {
                margin-top: 20px;
            }
            input, textarea {
                margin: 10px 0;
                padding: 5px;
            }
        </style>
    </head>
    <body>
        <h1>Document Processing and Speech-to-Text</h1>
        
        <div class="section">
            <h2>Document Upload</h2>
            <form id="uploadForm">
                <div>
                    <label for="file">Select PDF or DOCX file:</label><br>
                    <input type="file" id="file" name="file" accept=".pdf,.docx" required>
                </div>
                <div>
                    <label for="description">Description:</label><br>
                    <textarea id="description" name="description" required></textarea>
                </div>
                <button type="submit">Upload</button>
            </form>
            <div id="uploadResult"></div>
        </div>

        <div class="section">
            <h2>Live Speech to Text</h2>
            <button id="startButton">Start Recording</button>
            <button id="stopButton" disabled>Stop Recording</button>
            <div class="status" id="status">Not recording</div>
            <div id="result"></div>
        </div>

        <script>
            // Document upload handling
            document.getElementById('uploadForm').onsubmit = async (e) => {
                e.preventDefault();
                const formData = new FormData();
                formData.append('file', document.getElementById('file').files[0]);
                formData.append('description', document.getElementById('description').value);

                try {
                    const response = await fetch('/upload/document', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    document.getElementById('uploadResult').innerHTML = 
                        `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                } catch (error) {
                    console.error('Error:', error);
                }
            };

            // Speech-to-text handling
            const startButton = document.getElementById('startButton');
            const stopButton = document.getElementById('stopButton');
            const status = document.getElementById('status');
            const result = document.getElementById('result');
            
            let ws = null;
            let recognition = null;

            function initWebSocket() {
                ws = new WebSocket('ws://' + window.location.host + '/ws/speech-to-text');
                
                ws.onopen = () => {
                    console.log('WebSocket connected');
                };
                
                ws.onmessage = (event) => {
                    const response = JSON.parse(event.data);
                    console.log('Server response:', response);
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };
            }

            async function requestMicrophonePermission() {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    stream.getTracks().forEach(track => track.stop()); // Stop the stream after getting permission
                    return true;
                } catch (error) {
                    console.error('Microphone permission error:', error);
                    status.textContent = 'Error: Microphone permission denied. Please allow microphone access.';
                    return false;
                }
            }

            function initSpeechRecognition() {
                if (!window.SpeechRecognition && !window.webkitSpeechRecognition) {
                    status.textContent = 'Error: Speech recognition is not supported in this browser. Please use Chrome or Edge.';
                    return null;
                }

                recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
                recognition.interimResults = true;
                recognition.continuous = true;
                recognition.lang = 'en-US';

                recognition.onresult = (event) => {
                    const transcript = Array.from(event.results)
                        .map(result => result[0].transcript)
                        .join('');
                    
                    result.textContent = transcript;
                    
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(transcript);
                    }
                };

                recognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error);
                    if (event.error === 'not-allowed') {
                        status.textContent = 'Error: Microphone access denied. Please allow microphone access and try again.';
                    } else {
                        status.textContent = 'Error: ' + event.error;
                    }
                    stopButton.click(); // Stop recording on error
                };
            }

            startButton.onclick = async () => {
                // First check for microphone permission
                const hasPermission = await requestMicrophonePermission();
                if (!hasPermission) {
                    return;
                }

                initWebSocket();
                const recognitionInstance = initSpeechRecognition();
                if (!recognitionInstance && !recognition) {
                    return;
                }
                
                try {
                    recognition.start();
                    startButton.disabled = true;
                    stopButton.disabled = false;
                    status.textContent = 'Recording...';
                } catch (error) {
                    console.error('Error starting recognition:', error);
                    status.textContent = 'Error starting recognition. Please refresh and try again.';
                }
            };

            stopButton.onclick = () => {
                if (recognition) {
                    recognition.stop();
                }
                if (ws) {
                    ws.close();
                }
                startButton.disabled = false;
                stopButton.disabled = true;
                status.textContent = 'Not recording';
            };
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)