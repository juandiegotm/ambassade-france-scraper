import speech_recognition as sr
import audio_manager
import io

def solve_audio_captcha(captcha_audio):
    audio_wav = audio_manager.decode_to_wav(captcha_audio)
    binary_audio_data = audio_wav.read()
    return convertir_audio_a_texto(io.BytesIO(binary_audio_data))

def convertir_audio_a_texto(audio_data):
    reconocedor = sr.Recognizer()

    with sr.AudioFile(audio_data) as fuente_audio:
        audio_rec = reconocedor.record(fuente_audio)

        try:
            texto_transcripcion = reconocedor.recognize_google(audio_rec, language="es-ES")
            return clean_text(texto_transcripcion)
        except sr.UnknownValueError as err:
            print(err)
            return None
        
def clean_text(text):
    return text.replace(" ", "").upper()