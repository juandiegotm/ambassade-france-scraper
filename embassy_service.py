import json
from enum import Enum
import requests
import base64
import time
import logging
from datetime import date, timedelta
from helpers import Time, transform_date_format, transform_date_format_slot_value
from pprint import pformat
import sys

from captcha_solver import solve_audio_captcha
from notification_manager import NotificationManager

BASE_PATH = 'https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations/exclude-days'
GET_INTERVAL_PATH = 'https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations/get-interval?serviceId=623a31e505be16413d5f71ce'
BOT_TOKEN = ''
CHAT_ID = ''

START_DATE = '2024-01-17'
END_DATE = '2024-02-09'

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
        # Must be first, always.
        self.csrf_token = ""
        self.gouv_app_id = self.__get_gouv_app_id()

        # Even the server give us a start_date, we are interested in use the date defined by the user.
        self.start_date = START_DATE
        _, self.end_date = self.__get_interval()
        logger.info("Looking for dates in the period %s y %s", self.start_date, END_DATE)

        # TODO: session id has a duration of 30 minutes, so handle it to no request a lot from the server.
        self.session_id = self.__renovate_session()

    def main(self) -> Result: 
        dates = self.__avaliable_dates(START_DATE, END_DATE)
        if len(dates) == 0:
            logger.info(f"No available dates")
            return Result.RETRY
        else:
            wanted_date = list(dates.keys())[-1]
            wanted_hour = dates[wanted_date][0]
            #resultado = self.__create_reservation(wanted_date, wanted_hour)

            logger.info("Dates founded!")
            # logger.info(f"Intentado reservar {wanted_date} a las {wanted_hour}")
            sended = notificator.notify_available_days(pformat(dates, indent=2))
            if sended:
                logger.info("Notification send to telegram")
            else:
                logger.error("Cannot send notification to telegram. Check your secrets!")

            # if resultado:
            #      logger.info(f"Cita reservada con exito.")
            #      sys.exit()

            return Result.RETRY

    def __avaliable_dates(self, start_date, end_date):
        exclude_days = self.__get_exclude_days(start_date, end_date)
        possible_days = self.__generate_dates_interval(start_date, end_date)
        available_dates = list(possible_days-set(exclude_days))
        available_dates.sort()

        response = {}
        for date in available_dates:
            available_hours = self.__get_available_hours(date)
            if len(available_hours) > 0:
                response[date] = list(map(lambda x: x["time"], available_hours))
        
        return response
    
    
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
            self.csrf_token = csrf_token
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
    
    def __get_available_hours(self, day):
        url = "https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations/availability"
        payload = {
            "name": "VISAS ESTUDIANTES, ASSISTANTS DE LANGUE Y VVT",
            "date": day, 
            "places": 1,
            "maxCapacity": 1,
            "sessionId": self.session_id
        }

        response = requests.request("GET", url, headers=self.__get_cannonical_header(), params=payload)
        return response.json()
    
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
        url = "https://api.consulat.gouv.fr/api/captcha?locale=en"
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
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://consulat.gouv.fr/en/ambassade-de-france-a-bogota/appointment',
            'x-gouv-web': 'fr.gouv.consulat',
            'Content-Type': 'application/json',
            'Origin': 'https://consulat.gouv.fr',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'TE': 'trailers'
        }

        return requests.post(BASE_PATH, data=json.dumps(request_body), headers=headers)

    def __reservate_sesion(self):
        url = "https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations-session"
        
        payload = {
            'sessionId': self.session_id
        }
        return requests.request("GET", url, headers=self.__get_cannonical_header(), data=payload)
    

    def __create_reservation(self, str_date, hour):
        url = "https://api.consulat.gouv.fr/api/team/6230a5f8eb8eddc6026c2f86/reservations/family"

        h, m = list(map(lambda x: int(x), hour.split(":")))
        current_date = date.fromisoformat(str_date)

        slot_value = f"slot-visas-estudiantes-assistants-de-langue-y-vvt-{transform_date_format_slot_value(str_date, h, m)}"

        slot = {
            "time": hour,
            "rate": "0.00",
            "capacity": 1,
            "numberOfApplicants": 1,
            "date": str_date,
            "localDateString": (current_date-timedelta(days=1)).strftime("%-d/%-m/%Y"),
            "dateObject": {
                "year": current_date.year,
                "month": current_date.month-1,
                "day": current_date.weekday(),
                "hour": h,
                "minute": m
            },
            "id": 0,
            "slotValue": slot_value
        }

        payload = json.dumps({
        "reservations": {
            "mainUser": {
            "lastname": "",
            "firstname": "",
            "email": "",
            "mobile": "",
            "birthdate": {
                "day": 1,
                "month": 1,
                "year": 1999
            },
            "slots": {},
            "services": [
                {
                "zone": {
                    "name": "VISAS ESTUDIANTES, ASSISTANTS DE LANGUE Y VVT",
                    "name_traduction": {
                    "fr": "VISAS ESTUDIANTES, ASSISTANTS DE LANGUE Y VVT",
                    "en": "",
                    "zh": "",
                    "ar": "",
                    "ru": "",
                    "it": "",
                    "es": "",
                    "de": "",
                    "pt": ""
                    },
                    "enable_external_url": False,
                    "external_url": "",
                    "has_paid_reservation": False,
                    "openings": [
                    {
                        "day": 1,
                        "begin_h": 9,
                        "begin_m": 0,
                        "end_h": 12,
                        "end_m": 0,
                        "_id": "65a23d53c32275b643d26cbe"
                    },
                    {
                        "day": 2,
                        "begin_h": 9,
                        "begin_m": 0,
                        "end_h": 12,
                        "end_m": 0,
                        "_id": "65a23d53c32275b643d26cbf"
                    },
                    {
                        "day": 3,
                        "begin_h": 9,
                        "begin_m": 0,
                        "end_h": 12,
                        "end_m": 0,
                        "_id": "65a23d53c32275b643d26cc0"
                    },
                    {
                        "day": 4,
                        "begin_h": 9,
                        "begin_m": 0,
                        "end_h": 12,
                        "end_m": 0,
                        "_id": "65a23d53c32275b643d26cc1"
                    },
                    {
                        "day": 5,
                        "begin_h": 9,
                        "begin_m": 0,
                        "end_h": 11,
                        "end_m": 45,
                        "_id": "65a23d53c32275b643d26cc2"
                    }
                    ],
                    "custom_openings": [],
                    "breaktimes": [
                    [
                        {
                        "day": 1,
                        "begin_h": 10,
                        "begin_m": 0,
                        "end_h": 10,
                        "end_m": 15,
                        "_id": "65a23d53c32275b643d26cc3"
                        },
                        {
                        "day": 2,
                        "begin_h": 10,
                        "begin_m": 0,
                        "end_h": 10,
                        "end_m": 15,
                        "_id": "65a23d53c32275b643d26cc4"
                        },
                        {
                        "day": 3,
                        "begin_h": 10,
                        "begin_m": 0,
                        "end_h": 10,
                        "end_m": 15,
                        "_id": "65a23d53c32275b643d26cc5"
                        },
                        {
                        "day": 4,
                        "begin_h": 10,
                        "begin_m": 0,
                        "end_h": 10,
                        "end_m": 15,
                        "_id": "65a23d53c32275b643d26cc6"
                        },
                        {
                        "day": 5,
                        "begin_h": 10,
                        "begin_m": 30,
                        "end_h": 11,
                        "end_m": 0,
                        "_id": "65a23d53c32275b643d26cc7"
                        }
                    ]
                    ],
                    "session_duration": 15,
                    "session_type": "people",
                    "session_reservation_max": 1000,
                    "session_people_max": 2,
                    "reservation_people_max": 1,
                    "is_priority": False,
                    "reservation_delay_hours": 800,
                    "start_opening": "2022-05-31",
                    "end_opening": "2024-12-31",
                    "is_open": True,
                    "is_open_internal": True,
                    "stand_alone_calendar": False,
                    "note": {
                    "ar": "",
                    "de": "",
                    "en": "1/ Only applicants with this appointment receipt will be admitted within the Consulate. For security reasons, applicants are admitted to the Passport Office at set times only. Any person arriving late will not be received at the Consulate and will have to make a new appointment.\n\n2/ Before coming to your appointment, you should ensure that you have all the documents required to issue your passport or ID. For full details on the documents to be produced, please visit our website [https://co.ambafrance.org/-2-4-Passeports-CNIS-](https://co.ambafrance.org/-2-4-Passeports-CNIS-) . Incomplete applications will not be processed.\n\n**3/This appointment is for students visas and workholiday visas only. Workholiday visas for 2022 are not open.**",
                    "es": "1/ Sólo las personas con resguardo de cita serán admitidas en las oficinas. Por motivos de seguridad, el acceso al Servicio de Visados se realiza a las horas fijadas: las personas que lleguen tarde no podrán ser admitidas y deberán solicitar otra cita.\n\n\\*\\*2/ Esta cita solo permite solicitar una visa estudiante o una VVT (visa vacaciones trabajo). La campaña 2024 está abierta.  \n\\*\\*\n\n**3/Todos los solicitantes de una visa estudiante deben de pasar por la agencia Campus France Colombia** ****[https://www.colombie.campusfrance.org/](https://www.colombie.campusfrance.org/) y haber realizado**** ****su entrevista pedagógica**** con la agencia ++antes de la cita de visas++. Este proceso incluye a los menores escolarizados que planean realizar estudios superiores en Francia (post bachillerato).\n\n* * *\n\n4/ Antes de presentarse, asegúrese de que lleva todos los documentos exigidos para la expedición del visado. Para ello, consulte nuestra Web en la página de visados.  \n[https://co.ambafrance.org/Pedir-una-visa-en-Colombia-para-viajar-a-Francia](https://co.ambafrance.org/Pedir-una-visa-en-Colombia-para-viajar-a-Francia) y la página France Visas [https://france-visas.gouv.fr/](https://france-visas.gouv.fr/es/web/co/accueil)  \nLas solicitudes incompletas no podrán tramitarse. **Es OBLIGATORIO presentar el formulario de France Visas impreso, este formulario aparece después de haber creado una cuenta y realizado la solicitud de visa en línea.**",
                    "fr": "1/ Seules les personnes munies de cette convocation seront admises dans les locaux. Pour raisons de sécurité, l’entrée au service des visas se fait à heures fixes: les personnes en retard ne pourront être reçues et devront reprendre rendez-vous.\n\n**2/ Ce rendez-vous permet uniquement de demander un visa étudiant ou un VVT (visa vacances travail).** **Il ne permet pas de demander un autre type de visa.** \\*\\* La campagne VVT 2024 est ouverte.  \n\\*\\*\n\n**3/Tous les demandeurs de visas étudiants doivent passer par l’agence Campus France [https://www.colombie.campusfrance.org/](https://www.colombie.campusfrance.org/) et avoir réalisé l’entretien pédagogique avant le rendez-vous visa. Ce processus inclut les demandes de visas mineurs scolarisés pour des études supérieures (post-bac).**\n\n4/ Avant votre venue, assurez-vous d’être en possession de tous les documents nécessaires à la demande de visa. Pour cela, veuillez consulter notre site internet à la page [https://co.ambafrance.org/visas-7415](https://co.ambafrance.org/visas-7415) ainsi que France Visas [https://france-visas.gouv.fr/](https://france-visas.gouv.fr/es/web/co/)  \nLes dossiers incomplets ne pourront être traités. **Veuillez présenter le formulaire France Visas imprimé. Celui-ci apparait après avoir crée un compte puis réalisé la demande de visa en ligne.**",
                    "it": "",
                    "nl": "",
                    "pt": "",
                    "ru": "",
                    "zh": ""
                    },
                    "dynamic_calendar_enabled": True,
                    "dynamic_calendar_opening": {
                    "hour": "18",
                    "minute": "5"
                    },
                    "dynamic_calendar_ending": {
                    "hour": "default",
                    "minute": "default"
                    },
                    "external_link_for_documents": "https://co.ambafrance.org/-VISAS-971-",
                    "dynamic_calendar": {
                    "begin": {
                        "type": "days",
                        "value": 1
                    },
                    "end": {
                        "type": "days",
                        "value": 90
                    }
                    },
                    "closed_days": [
                    "2022-11-07",
                    "2022-11-14",
                    "2022-12-08",
                    "2022-12-25",
                    "2023-01-01",
                    "2023-01-09",
                    "2023-03-20",
                    "2023-04-06",
                    "2023-04-07",
                    "2023-05-01",
                    "2023-05-22",
                    "2023-06-12",
                    "2023-06-19",
                    "2023-07-03",
                    "2023-07-14",
                    "2023-07-20",
                    "2023-08-07",
                    "2023-08-21",
                    "2023-10-16",
                    "2023-11-06",
                    "2023-11-13",
                    "2023-12-08",
                    "2023-12-25",
                    "2024-01-01",
                    "2024-01-08",
                    "2024-03-25",
                    "2024-03-28",
                    "2024-03-29",
                    "2024-05-01",
                    "2024-05-08",
                    "2024-05-13",
                    "2024-06-03",
                    "2024-06-10",
                    "2024-07-01",
                    "2024-08-07",
                    "2024-08-19",
                    "2024-10-14",
                    "2024-11-04",
                    "2024-11-11",
                    "2024-12-25",
                    "2025-01-01"
                    ],
                    "custom_fields": [
                    {
                        "type": "selectList",
                        "label": "Motif",
                        "placeholder": "Quel est le motif de votre rendez-vous?",
                        "key": "6ad6fb78a4ad6657",
                        "required": True,
                        "unique": False,
                        "values": [
                        {
                            "name": "Visa étudiant (échange universitaire, double diplôme, bourse...)",
                            "translations": {
                            "fr": "Visa étudiant (échange universitaire, double diplôme, bourse...)"
                            }
                        },
                        {
                            "name": "Visa étudiant en séjour linguistique ",
                            "translations": {
                            "fr": "Visa étudiant en séjour linguistique "
                            }
                        },
                        {
                            "name": "Visa estudiante (intercambio, doble diploma, beca…)",
                            "translations": {
                            "es": "Visa estudiante (intercambio, doble diploma, beca…)"
                            }
                        },
                        {
                            "name": "Visa estudiante -estadía lingüística (escuela o curso de idioma francés)",
                            "translations": {
                            "es": "Visa estudiante -estadía lingüística (escuela o curso de idioma francés)"
                            }
                        },
                        {
                            "name": "Visa mineurs scolarisés en université ou école post-bac",
                            "translations": {
                            "fr": "Visa mineurs scolarisés en université ou école post-bac"
                            }
                        },
                        {
                            "name": "Visa menor escolarizado en universidad o después del bachillerato",
                            "translations": {
                            "es": "Visa menor escolarizado en universidad o después del bachillerato"
                            }
                        },
                        {
                            "name": "Assistant de langue",
                            "price": 0,
                            "translations": {
                            "fr": "Assistant de langue"
                            }
                        },
                        {
                            "name": "Asistente de lengua",
                            "price": 0,
                            "translations": {
                            "es": "Asistente de lengua"
                            }
                        },
                        {
                            "name": "Visa vacaciones trabajo-campaña 2024 abierta",
                            "price": 0,
                            "translations": {
                            "es": "Visa vacaciones trabajo-campaña 2024 abierta"
                            }
                        }
                        ],
                        "translations": {
                        "label": {
                            "fr": "Motif",
                            "en": "Motif",
                            "zh": "Motif",
                            "ru": "Motif",
                            "it": "Motif",
                            "es": "Motivo",
                            "ar": "Motif",
                            "de": "Motif",
                            "pt": "Motif",
                            "nl": "Motif"
                        },
                        "placeholder": {
                            "fr": "Quel est le motif de votre rendez-vous?",
                            "en": "Quel est le motif de votre rendez-vous?",
                            "zh": "Quel est le motif de votre rendez-vous?",
                            "ru": "Quel est le motif de votre rendez-vous?",
                            "it": "Quel est le motif de votre rendez-vous?",
                            "es": "Cuál es el motivo de su cita?",
                            "ar": "Quel est le motif de votre rendez-vous?",
                            "de": "Quel est le motif de votre rendez-vous?",
                            "pt": "Quel est le motif de votre rendez-vous?",
                            "nl": "Quel est le motif de votre rendez-vous?"
                        }
                        },
                        "_id": "65a23d53c32275b643d26cc8"
                    }
                    ],
                    "service_color": "#aaaaaa",
                    "enable_repeat_form": False,
                    "enable_fullday_slots": False,
                    "session_price": 0,
                    "cancel_limit": {
                    "value": 1,
                    "type": "days"
                    },
                    "activate_waiting_list": True,
                    "deactivate_reservation_cancelation": False,
                    "_id": "623a31e505be16413d5f71ce"
                },
                "zone_id": "623a31e505be16413d5f71ce",
                "external_link_for_documents": "https://co.ambafrance.org/-VISAS-971-",
                "label": "VISAS ESTUDIANTES, ASSISTANTS DE LANGUE Y VVT",
                "name": "VISAS ESTUDIANTES, ASSISTANTS DE LANGUE Y VVT",
                "numberOfSlots": 1,
                "maxSlots": 5,
                "checkboxesSlots": [
                    slot_value
                ],
                "customFields": [
                    {
                    "type": "selectList",
                    "label": "Motif",
                    "placeholder": "Quel est le motif de votre rendez-vous?",
                    "key": "6ad6fb78a4ad6657",
                    "required": True,
                    "unique": False,
                    "values": [
                        {
                        "name": "Visa vacaciones trabajo-campaña 2024 abierta",
                        "price": 0,
                        "translations": {
                            "es": "Visa vacaciones trabajo-campaña 2024 abierta"
                        }
                        }
                    ],
                    "translations": {
                        "label": {
                        "fr": "Motif",
                        "en": "Motif",
                        "zh": "Motif",
                        "ru": "Motif",
                        "it": "Motif",
                        "es": "Motivo",
                        "ar": "Motif",
                        "de": "Motif",
                        "pt": "Motif",
                        "nl": "Motif"
                        },
                        "placeholder": {
                        "fr": "Quel est le motif de votre rendez-vous?",
                        "en": "Quel est le motif de votre rendez-vous?",
                        "zh": "Quel est le motif de votre rendez-vous?",
                        "ru": "Quel est le motif de votre rendez-vous?",
                        "it": "Quel est le motif de votre rendez-vous?",
                        "es": "Cuál es el motivo de su cita?",
                        "ar": "Quel est le motif de votre rendez-vous?",
                        "de": "Quel est le motif de votre rendez-vous?",
                        "pt": "Quel est le motif de votre rendez-vous?",
                        "nl": "Quel est le motif de votre rendez-vous?"
                        }
                    },
                    "_id": "65a23d53c32275b643d26cc8"
                    }
                ],
                "customFieldsAreValid": True,
                "slots": [
                    slot
                ],
                "slotsToKeep": [
                    slot
                ]
                }
            ]
            },
            "secondaryUsers": [],
            "sessionId":  self.session_id,
            "team": "6230a5f8eb8eddc6026c2f86"
        },
        "language": "es",
        "sessionId":  self.session_id 
        })

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://consulat.gouv.fr/es/ambassade-de-france-a-bogota/appointment',
            'x-gouv-web': 'fr.gouv.consulat',
            'x-gouv-app-id': self.gouv_app_id,
            'Content-Type': 'application/json',
            'x-csrf-token': self.csrf_token,
            'Origin': 'https://consulat.gouv.fr',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'TE': 'trailers'
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        return response.status_code == 200
