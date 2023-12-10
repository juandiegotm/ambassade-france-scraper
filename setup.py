import time
import logging  
import json
import os
import subprocess

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

def as_lambda_function():
    data = {"retry_value": Time.RETRY_TIME // 60}
    temp_file = "json_var.json"
    with open(temp_file, "w") as write_file:
        json.dump(data, write_file, indent=4)
    subprocess.run(["sls", "deploy"], shell=True)
    os.remove(temp_file)

as_loop()