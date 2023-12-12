FROM public.ecr.aws/lambda/python:3.11

COPY ffmpeg ${LAMBDA_TASK_ROOT}/ffmpeg
RUN chmod 777 -R ${LAMBDA_TASK_ROOT}/ffmpeg
ENV PATH="/var/task/ffmpeg:${PATH}"

COPY requirements.txt ./
RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

COPY embassy_service.py ./
COPY captcha_solver.py ./
COPY notification_manager.py ./
COPY audio_manager.py ./
COPY helpers.py ./
COPY handler.py ./

CMD [ "handler.lambda_handler" ]


