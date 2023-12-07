from datetime import date, timedelta
import json
import requests
import time
import io
import base64
from pydub import AudioSegment
import speech_recognition as sr

START_DATE = '2024-01-22'
INTERVAL_IN_S = 60
SESSION_ID = '65712657236bf757bfe045b7'
BASE_PATH = 'https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations/exclude-days'
GET_INTERVAL_PATH = 'https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations/get-interval?serviceId=6233529437d20079e6271bd9'

FORMAT = '%Y-%m-%dT%X'


def send_captch(captcha, csrf_token):
    url = "https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations-session"

    payload = json.dumps({
        "sessionId": SESSION_ID,
        "captcha": "troov_c_" + captcha
    })
    headers = {
        'x-gouv-app-id': 'fr.gouv$+BOZwMiuRCyXjjKcyE9mMY29BoL7kJrhA%%1e407294-3fbd-4467-9758-1acdb4d25e09-meae-ttc',
        'Content-Type': 'application/json',
        'x-gouv-ck': csrf_token,
        'x-csrf-token': csrf_token
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    result = True if response.status_code == 200 else False
    return result

def get_captcha():
    url = "https://api.consulat.gouv.fr/api/captcha?locale=es"

    payload = {}
    headers = {
        'x-gouv-app-id': 'fr.gouv$+-4TyEFgeYq9yHSUQLv0_d2rmELDwOs6C%%4a376ffe-ca49-4c0c-b316-68056d15205b-meae-ttc'
    }
    
    response = requests.request("GET", url, headers=headers, data=payload)

    #write_audio(response.json()['audio'])

    return response.json(), response.headers['x-gouv-csrf']

def get_interval():
    headers = {
        'x-gouv-app-id': 'fr.gouv$+MhcFDqC7wspZ1T5j1f44rnFwkNDECfxZ%%33014d1f-5495-4cc6-a391-fab6f994840a-meae-ttc'
    }
    response = requests.request("GET", GET_INTERVAL_PATH, headers=headers)
    print(response.text)
    return response.json()

def request_exclude_days(start_date, end_date):
    request_body = {
        "start": transform_date_format(start_date),
        "end": transform_date_format(end_date),
        "session": {
            "623a31e505be16413d5f71ce": 1
        },
        "sessionId": SESSION_ID
    }

    headers = {
        'Content-Type': 'application/json',
        'x-gouv-app-id': 'fr.gouv$+MhcFDqC7wspZ1T5j1f44rnFwkNDECfxZ%%33014d1f-5495-4cc6-a391-fab6f994840a-meae-ttc'
    }

    response = requests.post(BASE_PATH, data=json.dumps(request_body), headers=headers)
    if response.status_code == 404:
        return None
    elif response.status_code == 429:
        raise Exception("El servidor detectó muchas peticiones en poco tiempo. Pausando 5 minutos")
    try: 
        exclude_days = response.json()
        return exclude_days
    except:
        raise Exception("Hubo un error cuyo status code es: " + str(response.status_code))


def get_exclude_days(start_date, end_date):
    answer = request_exclude_days(start_date, end_date)
    if not answer:
        print("No se puedo recuperar los días excluidos, renovando token...")
        renovado = False
        i = 0
        while i < 10:
            print(f"Intento {i}")
            renovado = renovate_session()
            
            if renovado:
                print("Sesión renovada")
                answer = request_exclude_days(start_date, end_date)
                print(answer)
                break
            else:
                print("Intento fallido, volviendo a internar...")
                time.sleep(5)
            i+=1
        
        if not renovado:
            raise Exception("No fue posible renovar el token luego de 10 intentos")

    return answer


def transform_date_format(request_date):
    return date.fromisoformat(request_date).strftime(FORMAT)


def send_notification():
    print("There is an avalible date")


def generate_dates_interval(start, end):
    dates = set()
    delta = timedelta(days=1)

    current_dt = date.fromisoformat(start)
    end_dt = date.fromisoformat(end)

    while current_dt <= end_dt:
        dates.add(current_dt.isoformat())
        current_dt += delta

    return dates

def avaliable_dates():
    interval_limits = get_interval()
    exclude_days = get_exclude_days(START_DATE, interval_limits['end'])
    if not exclude_days:
        return None
    
    possible_days = generate_dates_interval(START_DATE, interval_limits['end'])
    return list(possible_days-set(exclude_days))


# def png_to_svg(svg_data, file_style='cv2'):
#     png_data = cairosvg.svg2png(svg_data)
#     if file_style == 'cv2':
#         nparr = np.frombuffer(png_data, np.uint8)
#         img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#         cv2.imwrite('output_image.png', img)
#         return img
#     else:
#         img = Image.open(io.BytesIO(png_data))
#         img.save('output_image.png')
#         return(img)

# def improve_img(img, file_style='cv2'):
#     if file_style == 'cv2':
#         gry = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#         (h, w) = img.shape[:2]
#         gry = cv2.resize(gry, (w*3, h*3))
#         gry = cv2.medianBlur(gry, 5)
#         cv2.imwrite('gry.png', gry)

#         kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1,10))
#         cls = cv2.morphologyEx(gry, cv2.MORPH_CLOSE, kernel)
#         cv2.imwrite('cls.png', cls)
#         thr = cv2.threshold(cls, 50, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
#         cv2.imwrite('thr.png', thr)

#         _, im_inv = cv2.threshold(cls,127,255,cv2.THRESH_BINARY_INV)
#         cv2.imwrite('alternative.png', thr)
#         return thr
#     else:
#         width, height = img.size
#         new_size = (width * 3, height * 3)

#         resized_image = img.resize(new_size)
        
#         gray = resized_image.convert('L')
#         gray.save('captcha_gray.png')
#         # bw = gray.point(lambda x: 0 if x < 1 else 255, '1')
#         # bw.save('final.png')
#         return gray
    

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

def clean_text(text):
    return text.replace(" ", "").upper()

def write_audio(binary_audio_string):
    # Decodificar la cadena binaria
    binary_audio_data = base64.b64decode(binary_audio_string)

    # Crear un objeto BytesIO
    audio_data = io.BytesIO(binary_audio_data)

    # Crear un objeto AudioSegment a partir de los datos binarios
    audio_segment = AudioSegment.from_file(audio_data, format="mp3")

    # Guardar el archivo de audio
    audio_segment.export("output_audio.mp3", format="mp3")

def decode_to_wav(audio):
    binary_audio_data = base64.b64decode(audio)
    audio_data = io.BytesIO(binary_audio_data) 
    audio_segment = AudioSegment.from_file(audio_data, format="mp3")
    return audio_segment.export('output_audio.mp3',format="wav")

def solve_captcha(captcha_audio):
    audio_wav = decode_to_wav(captcha_audio)
    binary_audio_data = audio_wav.read()
    return convertir_audio_a_texto(io.BytesIO(binary_audio_data))

def renovate_session():
    data, csrf_token = get_captcha()
    audio_mp3_encoded = data['audio']
    captcha = solve_captcha(audio_mp3_encoded)
    return send_captch(captcha, csrf_token)

print("Iniciando servicio.")
while True:
    dates = avaliable_dates()
    if dates == None:
        print("Token vencido, renuevalo!")
        break
    elif len(dates) == 0:
        print(f"No hay fechas disponibles. Volviendo a intentar en {INTERVAL_IN_S} segundos...")
        time.sleep(INTERVAL_IN_S)
    else:
        send_notification()
        dates.sort()
        print(dates)
        break
