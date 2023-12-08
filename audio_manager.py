import io
from pydub import AudioSegment

def write_audio(binary_audio_data):
    audio_data = io.BytesIO(binary_audio_data)
    audio_segment = AudioSegment.from_file(audio_data, format="mp3")
    audio_segment.export("output_audio.mp3", format="mp3")

def decode_to_wav(binary_audio):
    audio_data = io.BytesIO(binary_audio) 
    audio_segment = AudioSegment.from_file(audio_data, format="mp3")
    #return audio_segment.export('output_audio.mp3',format="wav")
    return audio_segment.export(format="wav")