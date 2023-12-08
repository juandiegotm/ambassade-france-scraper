import time

from embassy_service import EmbassyService
from notification_manager import NotificationManager

START_DATE = '2024-01-22'
BOT_TOKEN = ''
CHAT_ID = ''
INTERVAL_IN_S = 120

def main():
    print("Iniciando servicio.")
    notificator = NotificationManager(BOT_TOKEN, CHAT_ID)
    embassy_service =  EmbassyService()

    # Even the server give us a start_date, 
    # we are interested in use the date defined by the user. 
    _, end_date = embassy_service.get_interval()
    
    print(f"Se buscarán citas en el periodo {START_DATE} y {end_date}")

    while True:
        dates = embassy_service.avaliable_dates(START_DATE, end_date)
        if len(dates) == 0:
            print(f"No hay fechas disponibles. Volviendo a intentar en {INTERVAL_IN_S} segundos...")
        else:
            dates.sort()
            notificator.notify_available_days(dates)
            print(f"¡Fechas encontradas! Volviendo a intentar en {INTERVAL_IN_S} segundos...")
        time.sleep(INTERVAL_IN_S)

main()