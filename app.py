from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from pydantic import BaseModel
import speech_recognition as sr
from docx import Document
import PyPDF2
import io
import json
from typing import List, Dict, Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request

# Import your existing components
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_groq import ChatGroq
from langgraph.graph import Graph
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
os.environ["GROQ_API_KEY"] = ""
os.environ["TAVILY_API_KEY"] = ""

app = FastAPI(title="Research Chatbot API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# In your app.py, replace the HTML_TEMPLATE with this:


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Research Assistant</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/github.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/marked/4.0.2/marked.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }

        body {
            background-color: #f7f7f8;
            height: 100vh;
            display: flex;
        }

        .sidebar {
            width: 260px;
            background-color: #202123;
            height: 100%;
            padding: 10px;
            display: flex;
            flex-direction: column;
        }

        .new-chat-btn {
            background-color: #343541;
            border: 1px solid #565869;
            border-radius: 5px;
            color: white;
            padding: 12px;
            width: 100%;
            text-align: left;
            margin-bottom: 15px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: background-color 0.3s;
        }

        .new-chat-btn:hover {
            background-color: #2D2E3A;
        }

        .chat-container {
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            height: 100%;
            position: relative;
            max-width: 1000px;
            margin: 0 auto;
            width: 100%;
        }

        .chat-header {
            padding: 15px;
            background-color: #ffffff;
            border-bottom: 1px solid #e5e5e5;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .chat-messages {
            flex-grow: 1;
            overflow-y: auto;
            padding: 20px;
            padding-bottom: 150px;
        }

        .message {
            display: flex;
            margin-bottom: 20px;
            padding: 20px;
            border-radius: 10px;
        }

        .user-message {
            background-color: #ffffff;
        }

        .assistant-message {
            background-color: #f7f7f8;
        }

        .message-avatar {
            width: 30px;
            height: 30px;
            border-radius: 5px;
            margin-right: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            color: white;
            flex-shrink: 0;
        }

        .user-avatar {
            background-color: #5437DB;
        }

        .assistant-avatar {
            background-color: #11A37F;
        }

        .message-content {
            flex-grow: 1;
            line-height: 1.5;
            overflow-wrap: break-word;
            min-width: 0;
        }

        /* Markdown Styling */
        .markdown-content h1 {
            font-size: 1.75em;
            margin: 1em 0 0.5em;
            color: #2c3e50;
        }

        .markdown-content h2 {
            font-size: 1.5em;
            margin: 1em 0 0.5em;
            color: #34495e;
        }

        .markdown-content h3 {
            font-size: 1.25em;
            margin: 1em 0 0.5em;
            color: #465669;
        }

        .markdown-content p {
            margin: 0.75em 0;
            line-height: 1.6;
        }

        .markdown-content ul, 
        .markdown-content ol {
            margin: 0.5em 0;
            padding-left: 2em;
        }

        .markdown-content li {
            margin: 0.3em 0;
        }

        .markdown-content blockquote {
            border-left: 4px solid #e0e0e0;
            margin: 1em 0;
            padding-left: 1em;
            color: #666;
        }

        .markdown-content code {
            background-color: #f5f5f5;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: monospace;
        }

        .markdown-content pre {
            background-color: #f5f5f5;
            padding: 1em;
            border-radius: 5px;
            overflow-x: auto;
            margin: 1em 0;
        }

        .markdown-content pre code {
            background-color: transparent;
            padding: 0;
        }

        .markdown-content strong {
            font-weight: 600;
            color: #2c3e50;
        }

        .markdown-content em {
            font-style: italic;
        }

        .markdown-content a {
            color: #0066cc;
            text-decoration: none;
        }

        .markdown-content a:hover {
            text-decoration: underline;
        }

        .markdown-content hr {
            border: none;
            border-top: 1px solid #e0e0e0;
            margin: 1.5em 0;
        }

        .markdown-content table {
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }

        .markdown-content th,
        .markdown-content td {
            border: 1px solid #e0e0e0;
            padding: 0.5em;
            text-align: left;
        }

        .markdown-content th {
            background-color: #f5f5f5;
        }

        .input-container {
            position: fixed;
            bottom: 0;
            width: calc(100% - 260px);
            max-width: 1000px;
            padding: 20px;
            background-color: #f7f7f8;
        }

        .input-box {
            display: flex;
            align-items: flex-end;
            gap: 10px;
            background-color: white;
            border: 1px solid #e5e5e5;
            border-radius: 10px;
            padding: 10px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }

        textarea {
            flex-grow: 1;
            border: none;
            resize: none;
            height: 24px;
            max-height: 200px;
            padding: 0;
            font-size: 16px;
            line-height: 1.5;
            outline: none;
        }

        .action-buttons {
            display: flex;
            gap: 10px;
        }

        .action-button {
            background: none;
            border: none;
            cursor: pointer;
            padding: 5px;
            color: #6e6e80;
            font-size: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: color 0.3s;
        }

        .action-button:hover {
            color: #11A37F;
        }

        .send-button {
            color: #11A37F;
        }

        .send-button:disabled {
            color: #6e6e80;
            cursor: not-allowed;
        }

        #fileInput {
            display: none;
        }

        .recording {
            color: #dc3545 !important;
        }

        .loading {
            display: inline-block;
            margin-left: 10px;
        }

        .loading:after {
            content: '.';
            animation: dots 1.5s steps(5, end) infinite;
        }

        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60% { content: '...'; }
            80%, 100% { content: ''; }
        }

        .error-message {
            color: #dc3545;
            margin-top: 5px;
            font-size: 14px;
        }

        @media (max-width: 768px) {
            .sidebar {
                display: none;
            }
            .input-container {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <button class="new-chat-btn">
            <i class="fas fa-plus"></i>
            New chat
        </button>
    </div>

    <div class="chat-container">
        <div class="chat-header">
            <i class="fas fa-robot"></i>
            AI Research Assistant
        </div>

        <div class="chat-messages" id="chatMessages">
            <div class="message assistant-message">
                <div class="message-avatar assistant-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <div class="markdown-content">
                        Hello! I'm your AI research assistant. I can help you with research queries through text, voice, or documents. How can I assist you today?
                    </div>
                </div>
            </div>
        </div>

        <div class="input-container">
            <div class="input-box">
                <textarea 
                    id="userInput" 
                    placeholder="Type your message here..." 
                    rows="1"
                    oninput="autoResize(this)"
                ></textarea>
                <div class="action-buttons">
                    <input type="file" id="fileInput" accept=".pdf,.docx" />
                    <button class="action-button" onclick="document.getElementById('fileInput').click()">
                        <i class="fas fa-paperclip"></i>
                    </button>
                    <button class="action-button" id="recordButton">
                        <i class="fas fa-microphone"></i>
                    </button>
                    <button class="action-button send-button" id="sendButton" disabled>
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
            </div>
            <div id="error" class="error-message"></div>
        </div>
    </div>

    <script>
        const API_BASE_URL = window.location.origin;
        let mediaRecorder;
        let audioChunks = [];
        let isRecording = false;

        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
            document.getElementById('sendButton').disabled = !textarea.value.trim();
        }

        function addMessage(content, isUser = false) {
            const messagesDiv = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
            
            const avatarDiv = document.createElement('div');
            avatarDiv.className = `message-avatar ${isUser ? 'user-avatar' : 'assistant-avatar'}`;
            avatarDiv.innerHTML = isUser ? 
                '<i class="fas fa-user"></i>' : 
                '<i class="fas fa-robot"></i>';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            
            if (isUser) {
                contentDiv.textContent = content;
            } else {
                marked.setOptions({
                    breaks: true,
                    gfm: true,
                    headerIds: true,
                    mangle: false,
                    sanitize: false,
                    smartLists: true,
                    smartypants: true,
                    xhtml: false
                });

                const markdownDiv = document.createElement('div');
                markdownDiv.className = 'markdown-content';
                markdownDiv.innerHTML = marked.parse(content);
                contentDiv.appendChild(markdownDiv);
            }

            messageDiv.appendChild(avatarDiv);
            messageDiv.appendChild(contentDiv);
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;

            if (!isUser && window.hljs) {
                messageDiv.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightBlock(block);
                });
            }
        }

        async function handleSubmit(text) {
            try {
                const response = await fetch(`${API_BASE_URL}/api/text`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ query: text })
                });

                if (!response.ok) throw new Error('Failed to get response');
                
                const data = await response.json();
                addMessage(data.result);
            } catch (error) {
                showError(error.message);
            }
        }

        document.getElementById('userInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const text = e.target.value.trim();
                if (text) {
                    addMessage(text, true);
                    handleSubmit(text);
                    e.target.value = '';
                    autoResize(e.target);
                }
            }
        });

        document.getElementById('sendButton').addEventListener('click', () => {
            const textarea = document.getElementById('userInput');
            const text = textarea.value.trim();
            if (text) {
                addMessage(text, true);
                handleSubmit(text);
                textarea.value = '';
                autoResize(textarea);
            }
        });

        document.getElementById('recordButton').addEventListener('click', async () => {
            const button = document.getElementById('recordButton');
            
            if (!isRecording) {
                try {
                            const response = await fetch(`${API_BASE_URL}/api/voice`, {
                                method: 'POST',
                                body: formData
                            });

                            if (!response.ok) throw new Error('Failed to process audio');
                            
                            const data = await response.json();
                            addMessage(data.result);
                        } catch (error) {
                            showError(error.message);
                        }
                    };

                    mediaRecorder.start();
                    isRecording = true;
                    button.querySelector('i').classList.add('recording');
                } catch (error) {
                    showError('Error accessing microphone: ' + error.message);
                }
            } else {
                mediaRecorder.stop();
                isRecording = false;
                button.querySelector('i').classList.remove('recording');
            }
        });

        document.getElementById('fileInput').addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            try {
                addMessage(`Processing file: ${file.name}`, true);
                const response = await fetch(`${API_BASE_URL}/api/document`, {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) throw new Error('Failed to process document');
                
                const data = await response.json();
                addMessage(data.result);
            } catch (error) {
                showError(error.message);
            }
            e.target.value = '';
        });

        function showError(message) {
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            setTimeout(() => {
                errorDiv.style.display = 'none';
            }, 5000);
        }

        document.querySelector('.new-chat-btn').addEventListener('click', () => {
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML = `
                <div class="message assistant-message">
                    <div class="message-avatar assistant-avatar">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div class="message-content">
                        <div class="markdown-content">
                            Hello! I'm your AI research assistant. I can help you with research queries through text, voice, or documents. How can I assist you today?
                        </div>
                    </div>
                </div>
            `;
        });
    </script>
</body>
</html>
"""



# HTML_TEMPLATE = """
# <!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>AI Research Assistant</title>
#     <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
#     <style>
#         * {
#             margin: 0;
#             padding: 0;
#             box-sizing: border-box;
#             font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
#         }

#         body {
#             background-color: #f7f7f8;
#             height: 100vh;
#             display: flex;
#         }

#         .sidebar {
#             width: 260px;
#             background-color: #202123;
#             height: 100%;
#             padding: 10px;
#             display: flex;
#             flex-direction: column;
#         }

#         .new-chat-btn {
#             background-color: #343541;
#             border: 1px solid #565869;
#             border-radius: 5px;
#             color: white;
#             padding: 12px;
#             width: 100%;
#             text-align: left;
#             margin-bottom: 15px;
#             cursor: pointer;
#             display: flex;
#             align-items: center;
#             gap: 12px;
#             transition: background-color 0.3s;
#         }

#         .new-chat-btn:hover {
#             background-color: #2D2E3A;
#         }

#         .chat-container {
#             flex-grow: 1;
#             display: flex;
#             flex-direction: column;
#             height: 100%;
#             position: relative;
#             max-width: 1000px;
#             margin: 0 auto;
#             width: 100%;
#         }

#         .chat-header {
#             padding: 15px;
#             background-color: #ffffff;
#             border-bottom: 1px solid #e5e5e5;
#             display: flex;
#             align-items: center;
#             gap: 10px;
#         }

#         .chat-messages {
#             flex-grow: 1;
#             overflow-y: auto;
#             padding: 20px;
#             padding-bottom: 150px;
#         }

#         .message {
#             display: flex;
#             margin-bottom: 20px;
#             padding: 20px;
#             border-radius: 10px;
#         }

#         .user-message {
#             background-color: #ffffff;
#         }

#         .assistant-message {
#             background-color: #f7f7f8;
#         }

#         .message-avatar {
#             width: 30px;
#             height: 30px;
#             border-radius: 5px;
#             margin-right: 15px;
#             display: flex;
#             align-items: center;
#             justify-content: center;
#             font-size: 14px;
#             color: white;
#         }

#         .user-avatar {
#             background-color: #5437DB;
#         }

#         .assistant-avatar {
#             background-color: #11A37F;
#         }

#         .message-content {
#             flex-grow: 1;
#             line-height: 1.5;
#         }

#         .input-container {
#             position: fixed;
#             bottom: 0;
#             width: calc(100% - 260px);
#             max-width: 1000px;
#             padding: 20px;
#             background-color: #f7f7f8;
#         }

#         .input-box {
#             display: flex;
#             align-items: flex-end;
#             gap: 10px;
#             background-color: white;
#             border: 1px solid #e5e5e5;
#             border-radius: 10px;
#             padding: 10px;
#             box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
#         }

#         textarea {
#             flex-grow: 1;
#             border: none;
#             resize: none;
#             height: 24px;
#             max-height: 200px;
#             padding: 0;
#             font-size: 16px;
#             line-height: 1.5;
#             outline: none;
#         }

#         .action-buttons {
#             display: flex;
#             gap: 10px;
#         }

#         .action-button {
#             background: none;
#             border: none;
#             cursor: pointer;
#             padding: 5px;
#             color: #6e6e80;
#             font-size: 20px;
#             display: flex;
#             align-items: center;
#             justify-content: center;
#             transition: color 0.3s;
#         }

#         .action-button:hover {
#             color: #11A37F;
#         }

#         .send-button {
#             color: #11A37F;
#         }

#         .send-button:disabled {
#             color: #6e6e80;
#             cursor: not-allowed;
#         }

#         #fileInput {
#             display: none;
#         }

#         .recording {
#             color: #dc3545 !important;
#         }

#         .loading {
#             display: inline-block;
#             margin-left: 10px;
#         }

#         .loading:after {
#             content: '.';
#             animation: dots 1.5s steps(5, end) infinite;
#         }

#         @keyframes dots {
#             0%, 20% { content: '.'; }
#             40% { content: '..'; }
#             60% { content: '...'; }
#             80%, 100% { content: ''; }
#         }

#         .error-message {
#             color: #dc3545;
#             margin-top: 5px;
#             font-size: 14px;
#         }

#         @media (max-width: 768px) {
#             .sidebar {
#                 display: none;
#             }
#             .input-container {
#                 width: 100%;
#             }
#         }
#     </style>
# </head>
# <body>
#     <div class="sidebar">
#         <button class="new-chat-btn">
#             <i class="fas fa-plus"></i>
#             New chat
#         </button>
#     </div>

#     <div class="chat-container">
#         <div class="chat-header">
#             <i class="fas fa-robot"></i>
#             AI Research Assistant
#         </div>

#         <div class="chat-messages" id="chatMessages">
#             <div class="message assistant-message">
#                 <div class="message-avatar assistant-avatar">
#                     <i class="fas fa-robot"></i>
#                 </div>
#                 <div class="message-content">
#                     Hello! I'm your AI research assistant. I can help you with research queries through text, voice, or documents. How can I assist you today?
#                 </div>
#             </div>
#         </div>

#         <div class="input-container">
#             <div class="input-box">
#                 <textarea 
#                     id="userInput" 
#                     placeholder="Type your message here..." 
#                     rows="1"
#                     oninput="autoResize(this)"
#                 ></textarea>
#                 <div class="action-buttons">
#                     <input type="file" id="fileInput" accept=".pdf,.docx" />
#                     <button class="action-button" onclick="document.getElementById('fileInput').click()">
#                         <i class="fas fa-paperclip"></i>
#                     </button>
#                     <button class="action-button" id="recordButton">
#                         <i class="fas fa-microphone"></i>
#                     </button>
#                     <button class="action-button send-button" id="sendButton" disabled>
#                         <i class="fas fa-paper-plane"></i>
#                     </button>
#                 </div>
#             </div>
#             <div id="error" class="error-message"></div>
#         </div>
#     </div>

#     <script>
#         const API_BASE_URL = window.location.origin;
#         let mediaRecorder;
#         let audioChunks = [];
#         let isRecording = false;

#         function autoResize(textarea) {
#             textarea.style.height = 'auto';
#             textarea.style.height = textarea.scrollHeight + 'px';
#             document.getElementById('sendButton').disabled = !textarea.value.trim();
#         }

#         function addMessage(content, isUser = false) {
#             const messagesDiv = document.getElementById('chatMessages');
#             const messageDiv = document.createElement('div');
#             messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
            
#             const avatarDiv = document.createElement('div');
#             avatarDiv.className = `message-avatar ${isUser ? 'user-avatar' : 'assistant-avatar'}`;
#             avatarDiv.innerHTML = isUser ? 
#                 '<i class="fas fa-user"></i>' : 
#                 '<i class="fas fa-robot"></i>';

#             const contentDiv = document.createElement('div');
#             contentDiv.className = 'message-content';
#             contentDiv.textContent = content;

#             messageDiv.appendChild(avatarDiv);
#             messageDiv.appendChild(contentDiv);
#             messagesDiv.appendChild(messageDiv);
#             messagesDiv.scrollTop = messagesDiv.scrollHeight;
#         }

#         async function handleSubmit(text) {
#             try {
#                 const response = await fetch(`${API_BASE_URL}/api/text`, {
#                     method: 'POST',
#                     headers: {
#                         'Content-Type': 'application/json',
#                     },
#                     body: JSON.stringify({ query: text })
#                 });

#                 if (!response.ok) throw new Error('Failed to get response');
                
#                 const data = await response.json();
#                 addMessage(data.result);
#             } catch (error) {
#                 showError(error.message);
#             }
#         }

#         document.getElementById('userInput').addEventListener('keypress', (e) => {
#             if (e.key === 'Enter' && !e.shiftKey) {
#                 e.preventDefault();
#                 const text = e.target.value.trim();
#                 if (text) {
#                     addMessage(text, true);
#                     handleSubmit(text);
#                     e.target.value = '';
#                     autoResize(e.target);
#                 }
#             }
#         });

#         document.getElementById('sendButton').addEventListener('click', () => {
#             const textarea = document.getElementById('userInput');
#             const text = textarea.value.trim();
#             if (text) {
#                 addMessage(text, true);
#                 handleSubmit(text);
#                 textarea.value = '';
#                 autoResize(textarea);
#             }
#         });

#         document.getElementById('recordButton').addEventListener('click', async () => {
#             const button = document.getElementById('recordButton');
            
#             if (!isRecording) {
#                 try {
#                     const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
#                     mediaRecorder = new MediaRecorder(stream);
#                     audioChunks = [];

#                     mediaRecorder.ondataavailable = (event) => {
#                         audioChunks.push(event.data);
#                     };

#                     mediaRecorder.onstop = async () => {
#                         const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
#                         const formData = new FormData();
#                         formData.append('audio', audioBlob, 'recording.wav');

#                         try {
#                             const response = await fetch(`${API_BASE_URL}/api/voice`, {
#                                 method: 'POST',
#                                 body: formData
#                             });

#                             if (!response.ok) throw new Error('Failed to process audio');
                            
#                             const data = await response.json();
#                             addMessage(data.result);
#                         } catch (error) {
#                             showError(error.message);
#                         }
#                     };

#                     mediaRecorder.start();
#                     isRecording = true;
#                     button.querySelector('i').classList.add('recording');
#                 } catch (error) {
#                     showError('Error accessing microphone: ' + error.message);
#                 }
#             } else {
#                 mediaRecorder.stop();
#                 isRecording = false;
#                 button.querySelector('i').classList.remove('recording');
#             }
#         });

#         document.getElementById('fileInput').addEventListener('change', async (e) => {
#             const file = e.target.files[0];
#             if (!file) return;

#             const formData = new FormData();
#             formData.append('file', file);

#             try {
#                 addMessage(`Processing file: ${file.name}`, true);
#                 const response = await fetch(`${API_BASE_URL}/api/document`, {
#                     method: 'POST',
#                     body: formData
#                 });

#                 if (!response.ok) throw new Error('Failed to process document');
                
#                 const data = await response.json();
#                 addMessage(data.result);
#             } catch (error) {
#                 showError(error.message);
#             }
#             e.target.value = '';
#         });

#         function showError(message) {
#             const errorDiv = document.getElementById('error');
#             errorDiv.textContent = message;
#             errorDiv.style.display = 'block';
#             setTimeout(() => {
#                 errorDiv.style.display = 'none';
#             }, 5000);
#         }

#         // New Chat button functionality
#         document.querySelector('.new-chat-btn').addEventListener('click', () => {
#             const chatMessages = document.getElementById('chatMessages');
#             chatMessages.innerHTML = `
#                 <div class="message assistant-message">
#                     <div class="message-avatar assistant-avatar">
#                         <i class="fas fa-robot"></i>
#                     </div>
#                     <div class="message-content">
#                         Hello! I'm your AI research assistant. I can help you with research queries through text, voice, or documents. How can I assist you today?
#                     </div>
#                 </div>
#             `;
#         });
#     </script>
# </body>
# </html>
# """













# # HTML template
# HTML_TEMPLATE = """
# <!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>Research Chatbot</title>
#     <style>
#         * {
#             margin: 0;
#             padding: 0;
#             box-sizing: border-box;
#             font-family: 'Arial', sans-serif;
#         }

#         body {
#             background-color: #f5f5f5;
#             padding: 20px;
#         }

#         .container {
#             max-width: 800px;
#             margin: 0 auto;
#             background: white;
#             padding: 20px;
#             border-radius: 10px;
#             box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
#         }

#         h1 {
#             text-align: center;
#             color: #333;
#             margin-bottom: 30px;
#         }

#         .input-section {
#             margin-bottom: 30px;
#             padding: 20px;
#             border: 1px solid #ddd;
#             border-radius: 8px;
#         }

#         .input-section h2 {
#             margin-bottom: 15px;
#             color: #444;
#         }

#         .text-input {
#             width: 100%;
#             padding: 10px;
#             margin-bottom: 10px;
#             border: 1px solid #ddd;
#             border-radius: 4px;
#             resize: vertical;
#             min-height: 100px;
#         }

#         .file-input {
#             margin-bottom: 10px;
#         }

#         .button {
#             background-color: #007bff;
#             color: white;
#             border: none;
#             padding: 10px 20px;
#             border-radius: 4px;
#             cursor: pointer;
#             transition: background-color 0.3s;
#         }

#         .button:hover {
#             background-color: #0056b3;
#         }

#         .button:disabled {
#             background-color: #cccccc;
#             cursor: not-allowed;
#         }

#         #recordButton {
#             background-color: #dc3545;
#         }

#         #recordButton.recording {
#             background-color: #28a745;
#         }

#         .result-section {
#             margin-top: 30px;
#             padding: 20px;
#             border: 1px solid #ddd;
#             border-radius: 8px;
#             display: none;
#         }

#         .result-section pre {
#             white-space: pre-wrap;
#             word-wrap: break-word;
#             background: #f8f9fa;
#             padding: 15px;
#             border-radius: 4px;
#         }

#         .loading {
#             text-align: center;
#             margin: 20px 0;
#             display: none;
#         }

#         .loading::after {
#             content: '';
#             display: inline-block;
#             width: 30px;
#             height: 30px;
#             border: 3px solid #f3f3f3;
#             border-top: 3px solid #3498db;
#             border-radius: 50%;
#             animation: spin 1s linear infinite;
#         }

#         @keyframes spin {
#             0% { transform: rotate(0deg); }
#             100% { transform: rotate(360deg); }
#         }

#         .error {
#             color: #dc3545;
#             margin-top: 10px;
#             display: none;
#         }
#     </style>
# </head>
# <body>
#     <div class="container">
#         <h1>Research Chatbot</h1>

#         <!-- Text Input Section -->
#         <div class="input-section">
#             <h2>Text Input</h2>
#             <textarea id="textInput" class="text-input" placeholder="Enter your research query here..."></textarea>
#             <button id="submitText" class="button">Submit Query</button>
#         </div>

#         <!-- Voice Input Section -->
#         <div class="input-section">
#             <h2>Voice Input</h2>
#             <button id="recordButton" class="button">Start Recording</button>
#             <div id="recordingStatus"></div>
#         </div>

#         <!-- Document Input Section -->
#         <div class="input-section">
#             <h2>Document Input</h2>
#             <input type="file" id="fileInput" class="file-input" accept=".pdf,.docx">
#             <button id="submitFile" class="button">Upload Document</button>
#         </div>

#         <!-- Loading Indicator -->
#         <div id="loading" class="loading"></div>

#         <!-- Error Message -->
#         <div id="error" class="error"></div>

#         <!-- Results Section -->
#         <div id="resultSection" class="result-section">
#             <h2>Results</h2>
#             <pre id="results"></pre>
#         </div>
#     </div>

#     <script>
#         const API_BASE_URL = window.location.origin;
#         let mediaRecorder;
#         let audioChunks = [];
#         let isRecording = false;

#         // Text submission
#         document.getElementById('submitText').addEventListener('click', async () => {
#             const text = document.getElementById('textInput').value.trim();
#             if (!text) {
#                 showError('Please enter a query');
#                 return;
#             }
            
#             try {
#                 showLoading();
#                 const response = await fetch(`${API_BASE_URL}/api/text`, {
#                     method: 'POST',
#                     headers: {
#                         'Content-Type': 'application/json',
#                     },
#                     body: JSON.stringify({ query: text })
#                 });

#                 if (!response.ok) throw new Error('Failed to get response');
                
#                 const data = await response.json();
#                 showResults(data.result);
#             } catch (error) {
#                 showError(error.message);
#             } finally {
#                 hideLoading();
#             }
#         });

#         // Voice recording
#         document.getElementById('recordButton').addEventListener('click', async () => {
#             const button = document.getElementById('recordButton');
#             const status = document.getElementById('recordingStatus');

#             if (!isRecording) {
#                 try {
#                     const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
#                     mediaRecorder = new MediaRecorder(stream);
#                     audioChunks = [];

#                     mediaRecorder.ondataavailable = (event) => {
#                         audioChunks.push(event.data);
#                     };

#                     mediaRecorder.onstop = async () => {
#                         const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
#                         const formData = new FormData();
#                         formData.append('audio', audioBlob, 'recording.wav');

#                         try {
#                             showLoading();
#                             const response = await fetch(`${API_BASE_URL}/api/voice`, {
#                                 method: 'POST',
#                                 body: formData
#                             });

#                             if (!response.ok) throw new Error('Failed to process audio');
                            
#                             const data = await response.json();
#                             showResults(data.result);
#                         } catch (error) {
#                             showError(error.message);
#                         } finally {
#                             hideLoading();
#                         }
#                     };

#                     mediaRecorder.start();
#                     isRecording = true;
#                     button.textContent = 'Stop Recording';
#                     button.classList.add('recording');
#                     status.textContent = 'Recording...';
#                 } catch (error) {
#                     showError('Error accessing microphone: ' + error.message);
#                 }
#             } else {
#                 mediaRecorder.stop();
#                 isRecording = false;
#                 button.textContent = 'Start Recording';
#                 button.classList.remove('recording');
#                 status.textContent = 'Recording stopped';
#             }
#         });

#         // File upload
#         document.getElementById('submitFile').addEventListener('click', async () => {
#             const fileInput = document.getElementById('fileInput');
#             const file = fileInput.files[0];
            
#             if (!file) {
#                 showError('Please select a file');
#                 return;
#             }

#             const formData = new FormData();
#             formData.append('file', file);

#             try {
#                 showLoading();
#                 const response = await fetch(`${API_BASE_URL}/api/document`, {
#                     method: 'POST',
#                     body: formData
#                 });

#                 if (!response.ok) throw new Error('Failed to process document');
                
#                 const data = await response.json();
#                 showResults(data.result);
#             } catch (error) {
#                 showError(error.message);
#             } finally {
#                 hideLoading();
#             }
#         });

#         // Utility functions
#         function showLoading() {
#             document.getElementById('loading').style.display = 'block';
#             document.getElementById('error').style.display = 'none';
#             document.getElementById('resultSection').style.display = 'none';
#         }

#         function hideLoading() {
#             document.getElementById('loading').style.display = 'none';
#         }

#         function showError(message) {
#             const errorDiv = document.getElementById('error');
#             errorDiv.textContent = message;
#             errorDiv.style.display = 'block';
#         }

#         function showResults(result) {
#             const resultSection = document.getElementById('resultSection');
#             const resultsDiv = document.getElementById('results');
#             resultsDiv.textContent = result;
#             resultSection.style.display = 'block';
#         }
#     </script>
# </body>
# </html>
# """

# Initialize components
llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.5
)

# Your existing workflow functions
def user_raw_query(input_1: str) -> str:
    return input_1

def user_query_optimize_node(input_2: str) -> str:
    prompt = f'''Modify this query for internet search to find research-focused results: "{input_2}" Return only the optimized search query without any additional text.'''
    response = llm.invoke(prompt).content
    return response

def search_node(input_3: str) -> List[Dict]:
    search = TavilySearchResults(max_results=2, search_depth="advanced")
    results = search.invoke(input_3)
    return results

def final_node(input_4: List[Dict]) -> str:
    sources = "\n".join([f"Source {i+1}: {result['url']}\nContent: {result['content']}\n" 
                        for i, result in enumerate(input_4)])
    prompt = f'''Generate a detailed research report based on the following sources: {sources}
    Format the report as follows:
    1. Executive Summary
    2. Key Findings
    3. Detailed Analysis
    4. Trends and Insights
    5. Citations
    Ensure all information is properly cited using [Source X] format.'''
    response = llm.invoke(prompt).content
    return response

# Setup workflow graph
workflow = Graph()
workflow.add_node("user_raw_query", user_raw_query)
workflow.add_node("user_query_optimize_node", user_query_optimize_node)
workflow.add_node("search_node", search_node)
workflow.add_node("final_node", final_node)
workflow.add_edge("user_raw_query", "user_query_optimize_node")
workflow.add_edge("user_query_optimize_node", "search_node")
workflow.add_edge("search_node", "final_node")
workflow.set_entry_point("user_raw_query")
workflow.set_finish_point("final_node")
app_workflow = workflow.compile()

# Pydantic models
class TextQuery(BaseModel):
    query: str

class Response(BaseModel):
    result: str

# Helper functions for processing different input types
def process_audio(audio_file: bytes) -> str:
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(io.BytesIO(audio_file)) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio)
            return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing audio: {str(e)}")

def process_pdf(pdf_file: bytes) -> str:
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing PDF: {str(e)}")

def process_docx(docx_file: bytes) -> str:
    try:
        doc = Document(io.BytesIO(docx_file))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing DOCX: {str(e)}")

# API endpoints
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return HTML_TEMPLATE

@app.post("/api/text", response_model=Response)
async def process_text_query(query: TextQuery):
    try:
        result = app_workflow.invoke(query.query)
        return Response(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice", response_model=Response)
async def process_voice_query(audio: UploadFile = File(...)):
    try:
        audio_bytes = await audio.read()
        text = process_audio(audio_bytes)
        result = app_workflow.invoke(text)
        return Response(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/document", response_model=Response)
async def process_document_query(file: UploadFile = File(...)):
    try:
        content = await file.read()
        if file.filename.endswith('.pdf'):
            text = process_pdf(content)
        elif file.filename.endswith('.docx'):
            text = process_docx(content)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        result = app_workflow.invoke(text)
        return Response(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
            