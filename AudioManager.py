import io
import speech_recognition as sr
from pydub import AudioSegment
from helpers import clean_text


def convertir_audio_a_texto(audio_data):
    reconocedor = sr.Recognizer()

    with sr.AudioFile(audio_data) as fuente_audio:
        audio_rec = reconocedor.record(fuente_audio)

        try:
            texto_transcripcion = reconocedor.recognize_google(audio_rec, language="es-ES")
            return clean_text(texto_transcripcion)
        except sr.UnknownValueError as err:
            print(err)
            # Manejar casos en los que no se pudo realizar la transcripción
            return "No se pudo transcribir el audio."

def write_audio(binary_audio_data):
    audio_data = io.BytesIO(binary_audio_data)
    audio_segment = AudioSegment.from_file(audio_data, format="mp3")
    audio_segment.export("output_audio.mp3", format="mp3")

def decode_to_wav(binary_audio):
    audio_data = io.BytesIO(binary_audio) 
    audio_segment = AudioSegment.from_file(audio_data, format="mp3")
    #return audio_segment.export('output_audio.mp3',format="wav")
    return audio_segment.export(format="wav")