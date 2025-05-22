import speech_recognition as sr

def test_voice_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Please speak into the microphone...")
        try:
            audio = recognizer.listen(source, timeout=5)
            print("Processing your input...")
            text = recognizer.recognize_google(audio)
            print(f"Recognized Text: {text}")
        except sr.WaitTimeoutError:
            print("No speech detected within the timeout period.")
        except sr.UnknownValueError:
            print("Could not understand the audio.")
        except sr.RequestError as e:
            print(f"Error with the speech recognition service: {e}")

if __name__ == "__main__":
    test_voice_to_text()