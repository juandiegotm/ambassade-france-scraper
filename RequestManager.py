import json
import requests
from helpers import transform_date_format

SESSION_ID = '657196db94525d7b9c8288dc'
GOUV_APP_ID = 'fr.gouv$+dSg17FCn1UNYbAdl82p5a0yH9U6ZNbIg%%0f78a9b2-27df-4692-a4c0-fa3214d42bb2-meae-ttc'

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

    response = requests.request("POST", url, headers=headers, data=payload)

    result = True if response.status_code == 200 else False
    return result

def get_captcha():
    url = "https://api.consulat.gouv.fr/api/captcha?locale=es"

    payload = {}
    headers = {
        'x-gouv-app-id': GOUV_APP_ID
    }
    
    response = requests.request("GET", url, headers=headers, data=payload)

    #write_audio(response.json()['audio'])

    return response.json(), response.headers['x-gouv-csrf']

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

    response = requests.post(BASE_PATH, data=json.dumps(request_body), headers=headers)
    if response.status_code == 404:
        return None
    elif response.status_code == 429:
        raise Exception("El servidor detectó muchas peticiones en poco tiempo. Pausando 5 minutos")
    try: 
        exclude_days = response.json()
        return exclude_days
    except:
        raise Exception("Hubo un error cuyo status code es: " + str(response.status_code))