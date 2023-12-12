import json
from enum import Enum
import requests
import base64
import time
import logging
from datetime import date, timedelta
from helpers import Time

from helpers import transform_date_format
from captcha_solver import solve_audio_captcha
from notification_manager import NotificationManager

BASE_PATH = 'https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations/exclude-days'
GET_INTERVAL_PATH = 'https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations/get-interval?serviceId=6233529437d20079e6271bd9'
BOT_TOKEN = ''
CHAT_ID = ''

START_DATE = '2024-01-22'

logger = logging.getLogger("Embassy_Logger")
notificator = NotificationManager(BOT_TOKEN, CHAT_ID)

class Result(Enum):
    SUCCESS = 1
    RETRY = 2
    COOLDOWN = 3
    EXCEPTION = 4

class EmbassyService:
    def __init__(self) -> None:
        logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
        logger.info("Process started")
        logger.info("Delay between queries: %ds", Time.RETRY_TIME)
        # Must be first, always.
        self.gouv_app_id = self.__get_gouv_app_id()

        # Even the server give us a start_date, we are interested in use the date defined by the user.
        self.start_date = START_DATE
        _, self.end_date = self.__get_interval()
        logger.info("Looking for dates in the period %s y %s", self.start_date, self.end_date)

        # TODO: session id has a duration of 30 minutes, so handle it to no request a lot from the server.
        self.session_id = self.__renovate_session()

    def main(self) -> Result: 
        dates = self.__avaliable_dates(START_DATE, self.end_date)
        if len(dates) == 0:
            logger.info(f"No available dates")
            return Result.RETRY

        else:
            logger.info("Dates founded!")
            dates.sort()
            sended = notificator.notify_available_days(dates)
            if sended:
                logger.info("Notification send to telegram")
            else:
                logger.error("Cannot send notification to telegram. Check your secrets!")
            return Result.SUCCESS 

    def __avaliable_dates(self, start_date, end_date):
        exclude_days = self.__get_exclude_days(start_date, end_date)
        possible_days = self.__generate_dates_interval(start_date, end_date)
        return list(possible_days-set(exclude_days))
    
    def __get_interval(self):
        body =  self.__request_get_interval().json()
        return body['start'], body['end']
    
    def __generate_dates_interval(self, start, end):
        dates = set()
        delta = timedelta(days=1)

        current_dt = date.fromisoformat(start)
        end_dt = date.fromisoformat(end)

        while current_dt <= end_dt:
            dates.add(current_dt.isoformat())
            current_dt += delta

        return dates

    def __get_exclude_days(self, start_date, end_date):
        response = self.__request_exclude_days(start_date, end_date)

        if response.status_code == 429:
            raise Exception("El servidor detectó muchas peticiones en poco tiempo. Pausando 5 minutos")

        if response.status_code == 200 and len(response.text) > 0:
            return response.json()
        
        logger.info("Experid session.")
        self.session_id = self.__renovate_session()

        new_response = self.__request_exclude_days(start_date, end_date)
        if new_response.status_code != 200:
            raise Exception("Hubo un problema inesperado: ", new_response.status_code, new_response.text)
        return new_response.json()
    
    def __get_session_id(self):
        get_captcha_response = self.__get_captcha()
        catpcha, csrf_token = get_captcha_response.json(), get_captcha_response.headers['x-gouv-csrf']

        binary_audio_data = base64.b64decode(catpcha['audio'])

        solution = solve_audio_captcha(binary_audio_data)
        if not solution or len(solution) != 4:
            return None
        
        response_send_captcha = self.__send_captcha(solution, csrf_token)
        try:
            body = response_send_captcha.json()
            return body['_id']
        except:
            return None
        
    def __renovate_session(self):
        logger.info("Getting a new session. Solving captcha (10 attemps)")
        session_id = None
        i = 0
        while i < 10:
            session_id = self.__get_session_id()
            
            if session_id:
                logger.info("Attempt %d: Succeed", i)
                break
            else:
                logger.info("Attempt %d: Failed", i)
                time.sleep(5)
            i+=1
        
        if not session_id:
            raise Exception("No fue posible renovar el token luego de 10 intentos")
        return session_id
    
    def __reservation_step(self):
        response_reservate_sesion = self.__reservate_sesion()
        body = response_reservate_sesion.json() 

        if not body['session']:
            Exception("El token no existe o es demasiado viejo. Renuevelo y vuelva a internarlo")

        return True if response_reservate_sesion.status_code == 200 else False
        
    def __get_gouv_app_id(self):
        return self.__request_hand_shake().headers['x-gouv-app-id']

    def __get_cannonical_header(self):
        return {
            'x-gouv-app-id': self.gouv_app_id
        }
    
    def __request_get_interval(self):
        headers = self.__get_cannonical_header()
        response = requests.request("GET", GET_INTERVAL_PATH, headers=headers)
        return response
    
    def __request_hand_shake(self):
        url = "https://api.consulat.gouv.fr/api/handshake"
        return requests.request("HEAD", url)
    
    def __send_captcha(self, captcha, csrf_token):
        url = "https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations-session"

        payload = json.dumps({
            "sessionId": None,
            "captcha": "troov_c_" + captcha
        })
        headers = {
            **self.__get_cannonical_header(),
            'Content-Type': 'application/json',
            'x-gouv-ck': csrf_token,
            'x-csrf-token': csrf_token
        }

        return requests.request("POST", url, headers=headers, data=payload)

    def __get_captcha(self):
        url = "https://api.consulat.gouv.fr/api/captcha?locale=es"
        return requests.request("GET", url, headers=self.__get_cannonical_header())

    def __request_exclude_days(self, start_date, end_date):
        request_body = {
            "start": transform_date_format(start_date),
            "end": transform_date_format(end_date),
            "session": {
                "623a31e505be16413d5f71ce": 1
            },
            "sessionId": self.session_id
        }

        headers = {
            **self.__get_cannonical_header(),
            'Content-Type': 'application/json',
        }
        return requests.post(BASE_PATH, data=json.dumps(request_body), headers=headers)

    def __reservate_sesion(self):
        url = "https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations-session"
        
        payload = {
            'sessionId': self.session_id
        }
        return requests.request("GET", url, headers=self.__get_cannonical_header(), data=payload)
