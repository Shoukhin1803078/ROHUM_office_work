import speech_recognition as sr
import pyttsx3

recognizer = sr.Recognizer()
# engine = pyttsx3.init()

# def speak(text):
#     engine.say(text)
#     engine.runAndWait()

print("Say something...")

try:
    # Listen to microphone
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    # Convert speech to text
    text = recognizer.recognize_google(audio)
    print(f"You said: {text}")
    
    # Convert text back to speech
    # speak(text)
    
except sr.UnknownValueError:
    print("Could not understand audio")
except sr.RequestError:
    print("Could not request results")