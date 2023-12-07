import time
import io
import base64

import RequestManager
import AudioManager
import NotificationManager
from helpers import generate_dates_interval

START_DATE = '2024-01-22'
INTERVAL_IN_S = 60

def solve_captcha(captcha_audio):
    audio_wav = AudioManager.decode_to_wav(captcha_audio)
    binary_audio_data = audio_wav.read()
    return AudioManager.convertir_audio_a_texto(io.BytesIO(binary_audio_data))

def renovate_session():
    # First, we have to make de reservation step. 
    reservation_step()
    renovado = False
    i = 0
    while i < 10:
        print(f"Intento {i}")
        renovado = captcha_step()
        
        if renovado:
            print("Catpcha solucionado con exito")
            break
        else:
            print("Intento fallido, volviendo a internar...")
            time.sleep(5)
        i+=1
    
    if not renovado:
        raise Exception("No fue posible renovar el token luego de 10 intentos")

    return renovado

def reservation_step():
    response_reservate_sesion = RequestManager.reservate_sesion()
    body = response_reservate_sesion.json()

    print(body)

    if not body['session']:
        Exception("El token no existe o es demasiado viejo. Renuevelo y vuelva a internarlo")

    return True if response_reservate_sesion.status_code == 200 else False
    

def captcha_step():
    get_captcha_response = RequestManager.get_captcha()
    catpcha, csrf_token = get_captcha_response.json(), get_captcha_response.headers['x-gouv-csrf']

    # Decodificar la cadena binaria
    binary_audio_data = base64.b64decode(catpcha['audio'])

    solution = solve_captcha(binary_audio_data)
    if len(solution) == 4:
        response_send_captcha = RequestManager.send_captch(solution, csrf_token)
        return True if response_send_captcha.status_code == 200 else False
    return False

def handle_exclude_days(response):
    if response.status_code == 200 and len(response.text) == 0:
        raise Exception('El header x-gouv-app-id está vencido, por favor renuevelo')
    elif response.status_code == 429:
        raise Exception("El servidor detectó muchas peticiones en poco tiempo. Pausando 5 minutos")

def get_exclude_days(start_date, end_date):
    response = RequestManager.request_exclude_days(start_date, end_date)
    handle_exclude_days(response)

    if response.status_code != 404:
        return response.json()
    
    print("No se puedo recuperar los días excluidos, renovando token...")
    
    new_response = RequestManager.request_exclude_days(start_date, end_date)
    if new_response.status_code != 200:
        raise Exception("Hubo un problema inesperado: ", new_response.status_code, new_response.text)
    return new_response.json()


def avaliable_dates(start_date, end_date):
    exclude_days = get_exclude_days(start_date, end_date)
    if not exclude_days:
        return None
    
    possible_days = generate_dates_interval(end_date, end_date)
    return list(possible_days-set(exclude_days))


def main():
    print("Iniciando servicio.")

    # Even the server give us a start_date, 
    # we are interested in use the date defined by the user. 
    interval_limits = RequestManager.get_interval()
    end_date = interval_limits['end']
    
    print(f"Se buscarán citas en el periodo {START_DATE} y {end_date}")

    while True:
        dates = avaliable_dates(START_DATE, end_date)
        if len(dates) == 0:
            print(f"No hay fechas disponibles. Volviendo a intentar en {INTERVAL_IN_S} segundos...")
            time.sleep(INTERVAL_IN_S)
        else:
            NotificationManager.send_notification()
            dates.sort()
            print(dates)
            break

main()