import boto3
import os
from embassy_service import EmbassyService
from helpers import Time

from pydub import AudioSegment

def lambda_handler(event, context):
    handler = EmbassyService()
    handler.main()
    event_arn = event["resources"][0]
    event_arn = event_arn[event_arn.rindex("/") + 1:]
    scheduler_client = boto3.client('scheduler')
    rate = Time.RETRY_TIME

    response = scheduler_client.get_schedule(Name=event_arn)
    scheduler_client.update_schedule(FlexibleTimeWindow=response["FlexibleTimeWindow"], Name=event_arn,
                                     ScheduleExpression=f"rate({rate // 60} minutes)", Target=response["Target"])