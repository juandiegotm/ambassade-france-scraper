import json
import requests
from helpers import transform_date_format

SESSION_ID = '65712657236bf757bfe045b7'
GOUV_APP_ID = 'fr.gouv$+rj_BOHWPWrqOyqXMys5lAuEbWPwnuoq8%%a4ee555b-c7dd-4979-a380-4ddeba9e1dfa-meae-ttc'

BASE_PATH = 'https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations/exclude-days'
GET_INTERVAL_PATH = 'https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations/get-interval?serviceId=6233529437d20079e6271bd9'

def send_captch(captcha, csrf_token):
    url = "https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations-session"

    payload = json.dumps({
        "sessionId": SESSION_ID,
        "captcha": "troov_c_" + captcha
    })
    headers = {
        'x-gouv-app-id': GOUV_APP_ID,
        'Content-Type': 'application/json',
        'x-gouv-ck': csrf_token,
        'x-csrf-token': csrf_token
    }

    return requests.request("POST", url, headers=headers, data=payload)

def get_captcha():
    url = "https://api.consulat.gouv.fr/api/captcha?locale=es"
    payload = {}
    headers = {
        'x-gouv-app-id': GOUV_APP_ID
    }

    return requests.request("GET", url, headers=headers, data=payload)

def get_interval():
    headers = {
        'x-gouv-app-id': GOUV_APP_ID,
    }
    response = requests.request("GET", GET_INTERVAL_PATH, headers=headers)
    return response.json()

def request_exclude_days(start_date, end_date):
    request_body = {
        "start": transform_date_format(start_date),
        "end": transform_date_format(end_date),
        "session": {
            "623a31e505be16413d5f71ce": 1
        },
        "sessionId": SESSION_ID
    }

    headers = {
        'Content-Type': 'application/json',
        'x-gouv-app-id': GOUV_APP_ID
    }

    return requests.post(BASE_PATH, data=json.dumps(request_body), headers=headers)

def reservate_sesion():
    url = "https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations-session"
    
    payload = {
        'sessionId': SESSION_ID
    }
    
    headers = {
        'x-gouv-app-id': GOUV_APP_ID
    }

    return requests.request("GET", url, headers=headers, data=payload)

    
