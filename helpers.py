from datetime import date

FORMAT = '%Y-%m-%dT%X'

def transform_date_format(request_date):
    return date.fromisoformat(request_date).strftime(FORMAT)

class Time:
    RETRY_TIME = 60 * 10  # wait time between retries/checks for available dates: 10 minutes
    # EXCEPTION_TIME = 60 * 30  # wait time when an exception occurs: 5 minutes
