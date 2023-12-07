import io
import speech_recognition as sr
from pydub import AudioSegment
from helpers import clean_text


def convertir_audio_a_texto(audio_data):
    # Configurar el reconocedor de voz
    reconocedor = sr.Recognizer()

    # Configurar el reconocedor para manejar el audio RAW
    with sr.AudioFile(audio_data) as fuente_audio:
        audio_rec = reconocedor.record(fuente_audio)

        try:
            # Realizar la transcripción del discurso
            texto_transcripcion = reconocedor.recognize_google(audio_rec, language="es-ES")
            return clean_text(texto_transcripcion)
        except sr.UnknownValueError as err:
            print(err)
            # Manejar casos en los que no se pudo realizar la transcripción
            return "No se pudo transcribir el audio."

def write_audio(binary_audio_data):
    # Crear un objeto BytesIO
    audio_data = io.BytesIO(binary_audio_data)

    # Crear un objeto AudioSegment a partir de los datos binarios
    audio_segment = AudioSegment.from_file(audio_data, format="mp3")

    # Guardar el archivo de audio
    audio_segment.export("output_audio.mp3", format="mp3")

def decode_to_wav(binary_audio):
    audio_data = io.BytesIO(binary_audio) 
    audio_segment = AudioSegment.from_file(audio_data, format="mp3")
    #return audio_segment.export('output_audio.mp3',format="wav")
    return audio_segment.export(format="wav")