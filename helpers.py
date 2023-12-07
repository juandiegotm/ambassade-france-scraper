from datetime import date, timedelta

FORMAT = '%Y-%m-%dT%X'

def clean_text(text):
    return text.replace(" ", "").upper()

def transform_date_format(request_date):
    return date.fromisoformat(request_date).strftime(FORMAT)

def generate_dates_interval(start, end):
    dates = set()
    delta = timedelta(days=1)

    current_dt = date.fromisoformat(start)
    end_dt = date.fromisoformat(end)

    while current_dt <= end_dt:
        dates.add(current_dt.isoformat())
        current_dt += delta

    return dates