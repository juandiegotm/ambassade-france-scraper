import time

from RequestManager import RequestManager
from NotificationManager import NotificationManager
from helpers import generate_dates_interval

START_DATE = '2024-01-22'
BOT_TOKEN = ''
CHAT_ID = ''
INTERVAL_IN_S = 120
request_manager =  RequestManager()


def handle_exclude_days(response):
    if response.status_code == 200 and len(response.text) == 0:
        raise Exception('Hubo una excepción extraña.')
    elif response.status_code == 429:
        raise Exception("El servidor detectó muchas peticiones en poco tiempo. Pausando 5 minutos")

def get_exclude_days(start_date, end_date):
    response = request_manager.request_exclude_days(start_date, end_date)
    handle_exclude_days(response)

    if response.status_code != 404:
        return response.json()
    
    print("No se puedo recuperar los días excluidos, renovando sesion...")
    request_manager.update_session()

    new_response = request_manager.request_exclude_days(start_date, end_date)
    if new_response.status_code != 200:
        raise Exception("Hubo un problema inesperado: ", new_response.status_code, new_response.text)
    return new_response.json()


def avaliable_dates(start_date, end_date):
    exclude_days = get_exclude_days(start_date, end_date)
    possible_days = generate_dates_interval(start_date, end_date)

    return list(possible_days-set(exclude_days))

def main():
    print("Iniciando servicio.")
    notificator = NotificationManager(BOT_TOKEN, CHAT_ID)

    # Even the server give us a start_date, 
    # we are interested in use the date defined by the user. 
    interval_limits = request_manager.get_interval()
    end_date = interval_limits['end']
    
    print(f"Se buscarán citas en el periodo {START_DATE} y {end_date}")

    while True:
        dates = avaliable_dates(START_DATE, end_date)
        if len(dates) == 0:
            print(f"No hay fechas disponibles. Volviendo a intentar en {INTERVAL_IN_S} segundos...")
        else:
            dates.sort()
            notificator.notify_available_days(dates)
            print(f"¡Fechas encontradas! Volviendo a intentar en {INTERVAL_IN_S} segundos...")
        time.sleep(INTERVAL_IN_S)

main()