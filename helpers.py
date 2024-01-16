from datetime import date, timedelta

FORMAT = '%Y-%m-%dT%X'

def transform_date_format(request_date):
    return date.fromisoformat(request_date).strftime(FORMAT)

def transform_date_format_slot_value(request_date, h, m):
    # 2024-04-11t00-00-00-000z-11-45
    f = "%Y-%m-%dt%H-%M-%S-000z"
    m_str = m if m != 0 else '00'
    date_searched = date.fromisoformat(request_date)
    return f"{date_searched.strftime(f)}-{h}-{m_str}" 


class Time:
    RETRY_TIME = 60 # wait time between retries/checks for available dates: 10 minutes
    EXCEPTION_TIME = 90  # wait time when an exception occurs: 1:30 minutes
