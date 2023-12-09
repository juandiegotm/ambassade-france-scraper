import time
import logging  
from helpers import Time

def as_loop():
    from embassy_service import EmbassyService, Result
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

    handler = EmbassyService()
    while True:        
        try:
            handler.main()
        except Exception as e:
            logging.error("Exception occurred", exc_info=True)

        time.sleep(Time.RETRY_TIME)


as_loop()