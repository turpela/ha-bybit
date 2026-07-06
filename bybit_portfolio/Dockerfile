FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache tzdata \
 && pip install --no-cache-dir requests

COPY app/main.py /

CMD ["python3", "/main.py"]
