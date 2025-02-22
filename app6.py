from fastapi import FastAPI, UploadFile, File, Form, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
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

# LangGraph nodes
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

# FastAPI endpoints
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            query_type = data.get("type", "text")
            query = data.get("query", "")
            context = ""

            if query_type == "document":
                # Process document text as context
                doc_text = data.get("document_text", "")
                context = doc_text

            # Process query through LangGraph
            try:
                response = process_query(query, context)
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

@app.post("/upload/document")
async def upload_document(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        
        if file.filename.endswith('.pdf'):
            text = await extract_pdf_text(contents)
        elif file.filename.endswith('.docx'):
            text = await extract_docx_text(contents)
        else:
            return {"error": "Unsupported file format"}
            
        return {"text": text}
    except Exception as e:
        return {"error": str(e)}

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
            .bot-message h1 { font-size: 1.5em; }
            .bot-message h2 { font-size: 1.3em; }
            .bot-message h3 { font-size: 1.1em; }
            .bot-message p {
                margin: 8px 0;
            }
            .bot-message ul, .bot-message ol {
                margin: 8px 0;
                padding-left: 20px;
            }
            .bot-message li {
                margin: 4px 0;
            }
            .bot-message code {
                background-color: #f0f0f0;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: monospace;
                font-size: 0.9em;
            }
            .bot-message pre {
                background-color: #f0f0f0;
                padding: 12px;
                border-radius: 4px;
                overflow-x: auto;
                margin: 8px 0;
            }
            .bot-message pre code {
                background-color: transparent;
                padding: 0;
            }
            .bot-message blockquote {
                border-left: 4px solid #ddd;
                margin: 8px 0;
                padding: 4px 12px;
                color: #666;
            }
            .bot-message table {
                border-collapse: collapse;
                margin: 8px 0;
                width: 100%;
            }
            .bot-message th, .bot-message td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            .bot-message th {
                background-color: #f0f0f0;
            }
            .bot-message strong {
                font-weight: 600;
            }
            .bot-message em {
                font-style: italic;
            }
            .input-container {
                display: flex;
                gap: 10px;
                align-items: flex-start;
            }
            textarea {
                flex-grow: 1;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
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
            .controls {
                display: flex;
                gap: 10px;
                margin-bottom: 10px;
            }
            .file-upload {
                display: none;
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
            <div class="chat-messages" id="chatMessages"></div>
            <div class="controls">
                <button id="uploadButton">📎 Upload Document</button>
                <button id="voiceButton">🎤 Voice Input</button>
                <input type="file" id="fileInput" class="file-upload" accept=".pdf,.docx">
                <div id="status" class="status"></div>
            </div>
            <div class="input-container">
                <textarea id="userInput" placeholder="Type your message here..."></textarea>
                <button id="sendButton">Send</button>
            </div>
        </div>

        <script>
            let ws = null;
            let recognition = null;
            const chatMessages = document.getElementById('chatMessages');
            const userInput = document.getElementById('userInput');
            const sendButton = document.getElementById('sendButton');
            const uploadButton = document.getElementById('uploadButton');
            const voiceButton = document.getElementById('voiceButton');
            const fileInput = document.getElementById('fileInput');
            const status = document.getElementById('status');

            let documentContext = "";

            function connectWebSocket() {
                ws = new WebSocket(`ws://${window.location.host}/ws/chat`);
                
                ws.onmessage = (event) => {
                    const response = JSON.parse(event.data);
                    if (response.status === 'success') {
                        addMessage(response.response, 'bot');
                    } else {
                        addMessage(`Error: ${response.message}`, 'bot');
                    }
                };

                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    status.textContent = 'Connection error. Please refresh the page.';
                };
            }

            function addMessage(text, sender) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${sender}-message`;
                
                if (sender === 'bot') {
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
                    
                    // Parse markdown and set innerHTML
                    messageDiv.innerHTML = marked.parse(text);
                    
                    // Apply syntax highlighting to code blocks
                    messageDiv.querySelectorAll('pre code').forEach(block => {
                        hljs.highlightElement(block);
                    });
                } else {
                    // Regular text for user messages
                    messageDiv.textContent = text;
                }
                
                chatMessages.appendChild(messageDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }

            async function sendMessage(text, type = 'text') {
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    connectWebSocket();
                }

                addMessage(text, 'user');
                
                const message = {
                    type: type,
                    query: text,
                    document_text: documentContext
                };

                ws.send(JSON.stringify(message));
            }

            // Event listeners
            sendButton.onclick = () => {
                const text = userInput.value.trim();
                if (text) {
                    sendMessage(text);
                    userInput.value = '';
                }
            };

            userInput.onkeypress = (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendButton.click();
                }
            };

            uploadButton.onclick = () => fileInput.click();

            fileInput.onchange = async (e) => {
                const file = e.target.files[0];
                if (!file) return;

                const formData = new FormData();
                formData.append('file', file);

                try {
                    status.textContent = 'Processing document...';
                    const response = await fetch('/upload/document', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    
                    if (data.error) {
                        status.textContent = `Error: ${data.error}`;
                    } else {
                        documentContext = data.text;
                        status.textContent = 'Document processed successfully!';
                        addMessage(`Document uploaded: ${file.name}`, 'user');
                    }
                } catch (error) {
                    status.textContent = 'Error processing document';
                    console.error('Error:', error);
                }
            };

            // Voice input handling
            voiceButton.onclick = async () => {
                if (!recognition) {
                    recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
                    recognition.continuous = false;
                    recognition.interimResults = false;
                    recognition.lang = 'en-US';

                    recognition.onresult = (event) => {
                        const transcript = event.results[0][0].transcript;
                        userInput.value = transcript;
                        status.textContent = 'Voice input received!';
                    };

                    recognition.onerror = (event) => {
                        status.textContent = `Error: ${event.error}`;
                    };
                }

                try {
                    status.textContent = 'Listening...';
                    recognition.start();
                } catch (error) {
                    status.textContent = 'Error starting voice recognition';
                    console.error('Error:', error);
                }
            };

            // Initialize WebSocket connection
            connectWebSocket();
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)