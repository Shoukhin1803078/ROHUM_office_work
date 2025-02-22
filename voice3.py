# pip install pydub ffmpeg-python

from fastapi import FastAPI, File, UploadFile
import speech_recognition as sr
import io
from pydub import AudioSegment

app = FastAPI()

@app.post("/voice-to-text/")
async def voice_to_text(file: UploadFile = File(...)):
    recognizer = sr.Recognizer()
    
    try:
        audio_data = await file.read()
        audio_file = io.BytesIO(audio_data)
        
        # Convert audio to WAV if not already in WAV format
        audio = AudioSegment.from_file(audio_file)
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)
        
        with sr.AudioFile(wav_io) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio)
        return {"transcription": text}
    except Exception as e:
        return {"error": "Could not process the audio", "details": str(e)}
