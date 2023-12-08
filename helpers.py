from datetime import date

FORMAT = '%Y-%m-%dT%X'

def transform_date_format(request_date):
    return date.fromisoformat(request_date).strftime(FORMAT)