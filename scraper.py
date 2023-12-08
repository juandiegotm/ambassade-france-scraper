import time
import logging  

from embassy_service import EmbassyService
from notification_manager import NotificationManager

START_DATE = '2024-01-22'
BOT_TOKEN = ''
CHAT_ID = ''
INTERVAL_IN_S = 120

def main():
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger()
    logger.info("Process started")

    notificator = NotificationManager(BOT_TOKEN, CHAT_ID)
    embassy_service =  EmbassyService()

    # Even the server give us a start_date, 
    # we are interested in use the date defined by the user. 
    _, end_date = embassy_service.get_interval()
    
    logger.info("Looking for dates in the period %s y %s", START_DATE, end_date)

    while True:
        dates = embassy_service.avaliable_dates(START_DATE, end_date)
        if len(dates) == 0:
            logger.info(f"No available dates. Trying again in %s seconds", INTERVAL_IN_S)
        else:
            dates.sort()
            notificator.notify_available_days(dates)
            logger.info(f"Dates Founded! Trying again in $s seconds...", INTERVAL_IN_S)
        time.sleep(INTERVAL_IN_S)

main()