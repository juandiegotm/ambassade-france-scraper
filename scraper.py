import time
import io
import base64

import RequestManager
import AudioManager
import NotificationManager

from helpers import generate_dates_interval

START_DATE = '2024-01-22'
INTERVAL_IN_S = 60

def get_exclude_days(start_date, end_date):
    answer = RequestManager.request_exclude_days(start_date, end_date)
    if not answer:
        print("No se puedo recuperar los días excluidos, renovando token...")
        renovado = False
        i = 0
        while i < 10:
            print(f"Intento {i}")
            renovado = renovate_session()
            
            if renovado:
                print("Sesión renovada")
                answer = RequestManager.request_exclude_days(start_date, end_date)
                break
            else:
                print("Intento fallido, volviendo a internar...")
                time.sleep(5)
            i+=1
        
        if not renovado:
            raise Exception("No fue posible renovar el token luego de 10 intentos")
    return answer


def avaliable_dates(start_date, end_date):
    exclude_days = get_exclude_days(start_date, end_date)
    if not exclude_days:
        return None
    
    possible_days = generate_dates_interval(end_date, end_date)
    return list(possible_days-set(exclude_days))
        

def solve_captcha(captcha_audio):
    audio_wav = AudioManager.decode_to_wav(captcha_audio)
    binary_audio_data = audio_wav.read()
    return AudioManager.convertir_audio_a_texto(io.BytesIO(binary_audio_data))

def renovate_session():
    data, csrf_token = RequestManager.get_captcha()
    audio_mp3_encoded = data['audio']

    # Decodificar la cadena binaria
    binary_audio_data = base64.b64decode(audio_mp3_encoded)

    captcha = solve_captcha(binary_audio_data)
    print("La resolución del captcha es: " + captcha)
    return RequestManager.send_captch(captcha, csrf_token)

def main():
    print("Iniciando servicio.")

    # Even the server give us a start_date, 
    # we are interested in use the date defined by the user. 
    interval_limits = RequestManager.get_interval()
    end_date = interval_limits['end']
    
    print(f"Se buscarán citas en el periodo {START_DATE} y {end_date}")

    while True:
        dates = avaliable_dates(START_DATE, end_date)
        if dates == None:
            print("Token vencido, renuevalo!")
            break
        elif len(dates) == 0:
            print(f"No hay fechas disponibles. Volviendo a intentar en {INTERVAL_IN_S} segundos...")
            time.sleep(INTERVAL_IN_S)
        else:
            NotificationManager.send_notification()
            dates.sort()
            print(dates)
            break

main()