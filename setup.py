import time
import logging  
import json
import os
import subprocess
import requests
import tarfile

import io

from helpers import Time

FFMPEG_STATIC_URL = "https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz"
OUTPUT_FOLDER = "./ffmpeg"

def as_loop():
    from embassy_service import EmbassyService

    handler = EmbassyService()
    while True:        
        try:
            handler.main()
        except Exception as e:
            logging.error("Exception occurred", exc_info=True)

        time.sleep(Time.RETRY_TIME)

def as_lambda_function():
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
    if not os.path.exists(OUTPUT_FOLDER):
        get_ffmpeg_folder()

    data = {"retry_value": Time.RETRY_TIME // 60}
    temp_file = "json_var.json"
    with open(temp_file, "w") as write_file:
        json.dump(data, write_file, indent=4)
    subprocess.run(["sls", "deploy"], shell=True)
    os.remove(temp_file)

def get_ffmpeg_folder():
    response = requests.get(FFMPEG_STATIC_URL)
    completed = False
    logging.info("Downloading file...")
    if response.status_code != 200:
        raise Exception("Can't download ffmpeg file. Try again.")
    
    binary_data = io.BytesIO(response.content)
    with tarfile.open(fileobj=binary_data, mode='r:xz') as tar:
        logging.info("Decompressing file...")
        tar.extractall("./")

    for entry in os.listdir("./"): 
        if entry.startswith("ffmpeg"):
            os.rename(entry, OUTPUT_FOLDER)
            completed = True
    
    if not completed:
        raise Exception("Can't download ffmpeg file. Try again.")