import json
import requests
import base64
import time
from datetime import date, timedelta

from helpers import transform_date_format
from captcha_solver import solve_audio_captcha

BASE_PATH = 'https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations/exclude-days'
GET_INTERVAL_PATH = 'https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations/get-interval?serviceId=6233529437d20079e6271bd9'

class EmbassyService:
    def __init__(self) -> None:
        self.gouv_app_id = self.__get_gouv_app_id()
        self.session_id = self.__renovate_session()

    def avaliable_dates(self, start_date, end_date):
        exclude_days = self.__get_exclude_days(start_date, end_date)
        possible_days = self.__generate_dates_interval(start_date, end_date)
        return list(possible_days-set(exclude_days))
    
    def get_interval(self):
        body =  self.__request_get_interval().json()
        return body['start'], body['end']
    
    def __request_get_interval(self):
        headers = {
            'x-gouv-app-id': self.gouv_app_id
        }
        response = requests.request("GET", GET_INTERVAL_PATH, headers=headers)
        return response
    
    def __generate_dates_interval(self, start, end):
        dates = set()
        delta = timedelta(days=1)

        current_dt = date.fromisoformat(start)
        end_dt = date.fromisoformat(end)

        while current_dt <= end_dt:
            dates.add(current_dt.isoformat())
            current_dt += delta

        return dates

    def __handle_exclude_days(self, response):
        if response.status_code == 200 and len(response.text) == 0:
            raise Exception('Hubo una excepción extraña.')
        elif response.status_code == 429:
            raise Exception("El servidor detectó muchas peticiones en poco tiempo. Pausando 5 minutos")

    def __get_exclude_days(self, start_date, end_date):
        response = self.__request_exclude_days(start_date, end_date)
        self.__handle_exclude_days(response)

        if response.status_code != 404:
            return response.json()
        
        print("No se puedo recuperar los días excluidos, renovando sesion...")
        self.session_id = self.__renovate_session()

        new_response = self.__request_exclude_days(self, start_date, end_date)
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
        
        response_send_captcha = self.__send_captch(solution, csrf_token)
        try:
            body = response_send_captcha.json()
            return body['_id']
        except:
            return None
        
    def __renovate_session(self):
        session_id = None
        i = 0
        while i < 10:
            print(f"Intento {i}")
            session_id = self.__get_session_id()
            
            if session_id:
                print("Catpcha solucionado con exito")
                break
            else:
                print("Intento fallido, volviendo a internar...")
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

    def __request_hand_shake(self):
        url = "https://api.consulat.gouv.fr/api/handshake"
        return requests.request("HEAD", url)
    
    def __get_gouv_app_id(self):
        return self.__request_hand_shake().headers['x-gouv-app-id']

    def __send_captch(self, captcha, csrf_token):
        url = "https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations-session"

        payload = json.dumps({
            "sessionId": None,
            "captcha": "troov_c_" + captcha
        })
        headers = {
            'x-gouv-app-id': self.gouv_app_id ,
            'Content-Type': 'application/json',
            'x-gouv-ck': csrf_token,
            'x-csrf-token': csrf_token
        }

        return requests.request("POST", url, headers=headers, data=payload)

    def __get_captcha(self):
        url = "https://api.consulat.gouv.fr/api/captcha?locale=es"
        payload = {}
        headers = {
            'x-gouv-app-id': self.gouv_app_id 
        }
        return requests.request("GET", url, headers=headers, data=payload)

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
            'Content-Type': 'application/json',
            'x-gouv-app-id': self.gouv_app_id 
        }
        return requests.post(BASE_PATH, data=json.dumps(request_body), headers=headers)

    def __reservate_sesion(self):
        url = "https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations-session"
        
        payload = {
            'sessionId': self.session_id
        }
        
        headers = {
            'x-gouv-app-id': self.gouv_app_id 
        }

        return requests.request("GET", url, headers=headers, data=payload)
