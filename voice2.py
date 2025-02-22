# pip install SpeechRecognition pyaudio
import speech_recognition as sr

recognizer = sr.Recognizer()

print("Speak something...")

with sr.Microphone() as source:
    recognizer.adjust_for_ambient_noise(source)
    audio = recognizer.listen(source)

try:
    text = recognizer.recognize_google(audio)
    print("You said:", text)
except:
    print("Could not understand audio")