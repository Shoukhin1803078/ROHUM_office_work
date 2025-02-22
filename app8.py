from fastapi import FastAPI, UploadFile, File, Form, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import asyncio
import json
from typing import List, Dict
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

app = FastAPI()

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

# 1. Text-only API endpoint
@app.websocket("/ws/text-only")
async def text_only_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            query = data.get("query", "")
            
            try:
                response = process_query(query)
                await websocket.send_json({
                    "status": "success",
                    "response": response
                })
            except Exception as e:
                await websocket.send_json({
                    "status": "error",
                    "message": str(e)
                })
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        await websocket.close()

# 2. Document with prompt API endpoint
@app.post("/upload/document-with-prompt")
async def document_with_prompt(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    description: Optional[str] = Form(None)
):
    try:
        contents = await file.read()
        
        if file.filename.endswith('.pdf'):
            text = await extract_pdf_text(contents)
        elif file.filename.endswith('.docx'):
            text = await extract_docx_text(contents)
        else:
            return {"error": "Unsupported file format"}
        
        # Process the document text with the prompt
        response = process_query(prompt, text)
        
        return {
            "status": "success",
            "filename": file.filename,
            "prompt": prompt,
            "description": description,
            "response": response
        }
    except Exception as e:
        return {"error": str(e)}

# 3. Voice with prompt API endpoint
@app.websocket("/ws/voice-with-prompt")
async def voice_with_prompt_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            voice_text = data.get("voice_text", "")
            prompt = data.get("prompt", "")
            
            try:
                # Combine voice input with prompt
                combined_query = f"{prompt}\nVoice Input: {voice_text}"
                response = process_query(combined_query)
                
                await websocket.send_json({
                    "status": "success",
                    "voice_text": voice_text,
                    "prompt": prompt,
                    "response": response
                })
            except Exception as e:
                await websocket.send_json({
                    "status": "error",
                    "message": str(e)
                })
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        await websocket.close()

@app.get("/", response_class=HTMLResponse)
async def get_html():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Research Chatbot</title>
        <!-- Add markdown and syntax highlighting libraries -->
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/default.min.css">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js"></script>
        <style>
            /* Your existing styles */
            body {
                font-family: Arial, sans-serif;
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .chat-container {
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                padding: 20px;
                margin-bottom: 20px;
            }
            /* Add tab styles */
            .tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
            }
            .tab {
                padding: 10px 20px;
                background-color: #e3f2fd;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            .tab.active {
                background-color: #2196f3;
                color: white;
            }
            .tab-content {
                display: none;
            }
            .tab-content.active {
                display: block;
            }
            /* Your other existing styles */
            .chat-messages {
                height: 500px;
                overflow-y: auto;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .message {
                margin-bottom: 15px;
                padding: 10px;
                border-radius: 5px;
            }
            .user-message {
                background-color: #e3f2fd;
                margin-left: 20%;
            }
            .bot-message {
                background-color: #f5f5f5;
                margin-right: 20%;
                line-height: 1.5;
            }
            /* Markdown styles */
            .bot-message h1, .bot-message h2, .bot-message h3 {
                margin-top: 16px;
                margin-bottom: 8px;
                font-weight: 600;
            }
            .bot-message code {
                background-color: #f0f0f0;
                padding: 2px 4px;
                border-radius: 3px;
            }
            .input-container {
                display: flex;
                gap: 10px;
                align-items: flex-start;
                margin-top: 10px;
            }
            .prompt-container {
                margin-bottom: 15px;
            }
            textarea, input[type="text"] {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-bottom: 10px;
            }
            textarea {
                height: 60px;
                resize: none;
            }
            button {
                padding: 10px 20px;
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            button:disabled {
                background-color: #ccc;
            }
            .status {
                color: #666;
                margin-top: 5px;
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <h1>Research Chatbot</h1>
            <div class="tabs">
                <button class="tab active" data-tab="text-only">Text Only</button>
                <button class="tab" data-tab="document">Document Upload</button>
                <button class="tab" data-tab="voice">Voice Input</button>
            </div>

            <!-- Text Only Tab -->
            <div id="text-only" class="tab-content active">
                <div class="chat-messages" id="textOnlyMessages"></div>
                <div class="input-container">
                    <textarea id="textOnlyInput" placeholder="Type your query here..."></textarea>
                    <button id="textOnlySend">Send</button>
                </div>
            </div>

            <!-- Document Upload Tab -->
            <div id="document" class="tab-content">
                <div class="prompt-container">
                    <textarea id="documentPrompt" placeholder="Enter your prompt/question about the document..."></textarea>
                    <input type="text" id="documentDescription" placeholder="Description (optional)">
                    <div class="input-container">
                        <input type="file" id="fileInput" accept=".pdf,.docx">
                        <button id="uploadButton">Upload & Process</button>
                    </div>
                </div>
                <div class="chat-messages" id="documentMessages"></div>
            </div>

            <!-- Voice Input Tab -->
            <div id="voice" class="tab-content">
                <div class="prompt-container">
                    <textarea id="voicePrompt" placeholder="Enter context or instructions for voice input..."></textarea>
                    <textarea id="voiceTranscript" placeholder="Your voice input will appear here for review..." readonly></textarea>
                    <div class="button-group">
                        <button id="voiceButton">🎤 Start Recording</button>
                        <button id="voiceSubmit" disabled>Submit</button>
                    </div>
                </div>
                <div id="voiceStatus" class="status">Not recording</div>
                <div class="chat-messages" id="voiceMessages"></div>
            </div>
        </div>

        <script>
            // Tab switching logic
            const tabs = document.querySelectorAll('.tab');
            const tabContents = document.querySelectorAll('.tab-content');

            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    const tabId = tab.getAttribute('data-tab');
                    
                    // Update active tab
                    tabs.forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');
                    
                    // Update active content
                    tabContents.forEach(content => {
                        content.classList.remove('active');
                        if (content.id === tabId) {
                            content.classList.add('active');
                        }
                    });
                });
            });

            // Markdown rendering function
            function renderMarkdown(text, targetElement) {
                // Configure marked options
                marked.setOptions({
                    breaks: true,
                    gfm: true,
                    highlight: function(code, language) {
                        if (language && hljs.getLanguage(language)) {
                            return hljs.highlight(code, { language }).value;
                        }
                        return code;
                    }
                });
                
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message bot-message';
                messageDiv.innerHTML = marked.parse(text);
                
                messageDiv.querySelectorAll('pre code').forEach(block => {
                    hljs.highlightElement(block);
                });
                
                targetElement.appendChild(messageDiv);
                targetElement.scrollTop = targetElement.scrollHeight;
            }

            // Add user message function
            function addUserMessage(text, targetElement) {
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message user-message';
                messageDiv.textContent = text;
                targetElement.appendChild(messageDiv);
                targetElement.scrollTop = targetElement.scrollHeight;
            }

            // Text-only chat functionality
            let textOnlyWs = new WebSocket(`ws://${window.location.host}/ws/text-only`);
            const textOnlyMessages = document.getElementById('textOnlyMessages');
            const textOnlyInput = document.getElementById('textOnlyInput');
            const textOnlySend = document.getElementById('textOnlySend');

            textOnlyWs.onmessage = (event) => {
                const response = JSON.parse(event.data);
                if (response.status === 'success') {
                    renderMarkdown(response.response, textOnlyMessages);
                }
            };

            textOnlySend.onclick = () => {
                const text = textOnlyInput.value.trim();
                if (text) {
                    addUserMessage(text, textOnlyMessages);
                    textOnlyWs.send(JSON.stringify({ query: text }));
                    textOnlyInput.value = '';
                }
            };

            // Document upload functionality
            const documentPrompt = document.getElementById('documentPrompt');
            const documentDescription = document.getElementById('documentDescription');
            const fileInput = document.getElementById('fileInput');
            const uploadButton = document.getElementById('uploadButton');
            const documentMessages = document.getElementById('documentMessages');

            uploadButton.onclick = async () => {
                const file = fileInput.files[0];
                const prompt = documentPrompt.value.trim();
                if (!file || !prompt) {
                    alert('Please select a file and enter a prompt');
                    return;
                }

                const formData = new FormData();
                formData.append('file', file);
                formData.append('prompt', prompt);
                formData.append('description', documentDescription.value);

                try {
                    const response = await fetch('/upload/document-with-prompt', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    if (data.error) {
                        alert(`Error: ${data.error}`);
                    } else {
                        addUserMessage(`Uploaded: ${file.name}\nPrompt: ${prompt}`, documentMessages);
                        renderMarkdown(data.response, documentMessages);
                    }
                } catch (error) {
                    alert('Error processing document: ' + error.message);
                }
            };

            // Voice input functionality
            let voiceWs = new WebSocket(`ws://${window.location.host}/ws/voice-with-prompt`);
            const voiceButton = document.getElementById('voiceButton');
            const voiceSubmit = document.getElementById('voiceSubmit');
            const voicePrompt = document.getElementById('voicePrompt');
            const voiceTranscript = document.getElementById('voiceTranscript');
            const voiceStatus = document.getElementById('voiceStatus');
            const voiceMessages = document.getElementById('voiceMessages');
            let recognition = null;

            voiceWs.onmessage = (event) => {
                const response = JSON.parse(event.data);
                if (response.status === 'success') {
                    renderMarkdown(response.response, voiceMessages);
                }
            };

            voiceButton.onclick = async () => {
                if (!recognition) {
                    recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
                    recognition.continuous = false;
                    recognition.interimResults = false;
                    recognition.lang = 'en-US';

                    recognition.onresult = (event) => {
                        const transcript = event.results[0][0].transcript;
                        voiceTranscript.value = transcript;
                        voiceSubmit.disabled = false;
                        voiceStatus.textContent = 'Voice input received! Review and submit.';
                    };

                    recognition.onerror = (event) => {
                        voiceStatus.textContent = `Error: ${event.error}`;
                    };
                }

                try {
                    voiceStatus.textContent = 'Listening...';
                    voiceTranscript.value = '';
                    voiceSubmit.disabled = true;
                    recognition.start();
                } catch (error) {
                    voiceStatus.textContent = 'Error starting voice recognition';
                    console.error('Error:', error);
                }
            };

            voiceSubmit.onclick = () => {
                const transcript = voiceTranscript.value.trim();
                const prompt = voicePrompt.value.trim();
                
                if (transcript && prompt) {
                    addUserMessage(`Voice Input: ${transcript}\nPrompt: ${prompt}`, voiceMessages);
                    voiceWs.send(JSON.stringify({
                        voice_text: transcript,
                        prompt: prompt
                    }));
                    
                    // Reset the form
                    voiceTranscript.value = '';
                    voiceSubmit.disabled = true;
                    voiceStatus.textContent = 'Voice input submitted!';
                } else {
                    voiceStatus.textContent = 'Please provide both voice input and prompt.';
                }
            };

            // WebSocket reconnection logic
            function setupWebSocketReconnection(ws, url) {
                ws.onclose = () => {
                    console.log('WebSocket closed. Reconnecting...');
                    setTimeout(() => {
                        ws = new WebSocket(url);
                        setupWebSocketReconnection(ws, url);
                    }, 1000);
                };
            }

            setupWebSocketReconnection(textOnlyWs, `ws://${window.location.host}/ws/text-only`);
            setupWebSocketReconnection(voiceWs, `ws://${window.location.host}/ws/voice-with-prompt`);
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)