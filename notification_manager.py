import requests
import json

class NotificationManager:
    def __init__(self, bot_token, chat_id) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    def notify_available_days(self, dates):
        response = self.__send_telegram_message("Los días disponibles son: \n" + str(dates))
        return True if response.status_code == 200 else False

    def __send_telegram_message(self, message: str):
        headers = {'Content-Type': 'application/json',
                'Proxy-Authorization': 'Basic base64'}
        data_dict = {'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': 'HTML',
                    'disable_notification': True}
        data = json.dumps(data_dict)
        url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'
        response = requests.post(url,
                                data=data,
                                headers=headers)
        return response