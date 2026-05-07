import sounddevice as sd
import queue
import json
from vosk import Model, KaldiRecognizer
import win32com.client
import pythoncom




class voice_engine:
    def __init__(self):
        self.q = queue.Queue()
        pythoncom.CoUninitialize()
        self.vengine = win32com.client.Dispatch("SAPI.SpVoice")
        self.modelpath = "model/vosk-model-small-en-in-0.4"
        self.model = Model(self.modelpath)
        

    def callback(self, indata, frames, time, status):
        self.q.put(bytes(indata))

    def recognizer(self, word = "start"):
        recognizer = KaldiRecognizer(self.model,16000)
        stream = sd.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype='int16',
            channels=1,
            callback=self.callback
        )
        with stream:
            while True:
                data = self.q.get()
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text","")
                    print("Heard:",text)

                    if word in text:
                        print(f"{word} detected - Activated!")
                        self.vengine.Speak(f"I am {word}ing. ")
                        return 1



    

if __name__=="__main__":
    ve = voice_engine()
    ve.recognizer()