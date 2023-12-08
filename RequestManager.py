import json
import requests
import base64
from helpers import transform_date_format
import time
import io

import AudioManager

BASE_PATH = 'https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations/exclude-days'
GET_INTERVAL_PATH = 'https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations/get-interval?serviceId=6233529437d20079e6271bd9'

class RequestManager:
    def __init__(self) -> None:
        self.gouv_app_id = self.__get_gouv_app_id()
        self.session_id = self.__renovate_session()

    def update_session(self):
        self.session_id = self.__renovate_session()

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

    def get_captcha(self):
        url = "https://api.consulat.gouv.fr/api/captcha?locale=es"
        payload = {}
        headers = {
            'x-gouv-app-id': self.gouv_app_id 
        }

        return requests.request("GET", url, headers=headers, data=payload)

    def get_interval(self):
        headers = {
            'x-gouv-app-id': self.gouv_app_id
        }
        response = requests.request("GET", GET_INTERVAL_PATH, headers=headers)
        return response.json()

    def request_exclude_days(self, start_date, end_date):
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

    def reservate_sesion(self):
        url = "https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations-session"
        
        payload = {
            'sessionId': self.session_id
        }
        
        headers = {
            'x-gouv-app-id': self.gouv_app_id 
        }

        return requests.request("GET", url, headers=headers, data=payload)
    
    def __renovate_session(self):
        session_id = None
        i = 0
        while i < 10:
            print(f"Intento {i}")
            session_id = self._get_session_id()
            
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

    
    def _get_session_id(self):
        get_captcha_response = self.get_captcha()
        catpcha, csrf_token = get_captcha_response.json(), get_captcha_response.headers['x-gouv-csrf']

        binary_audio_data = base64.b64decode(catpcha['audio'])

        solution = self.solve_captcha(binary_audio_data)
        if len(solution) != 4:
            return None
        
        response_send_captcha = self.__send_captch(solution, csrf_token)
        try:
            body = response_send_captcha.json()
            return body['_id']
        except:
            return None
        
    def solve_captcha(self, captcha_audio):
        audio_wav = AudioManager.decode_to_wav(captcha_audio)
        binary_audio_data = audio_wav.read()
        return AudioManager.convertir_audio_a_texto(io.BytesIO(binary_audio_data))
    
    def reservation_step(self):
        response_reservate_sesion = self.reservate_sesion()
        body = response_reservate_sesion.json() 

        if not body['session']:
            Exception("El token no existe o es demasiado viejo. Renuevelo y vuelva a internarlo")

        return True if response_reservate_sesion.status_code == 200 else False
