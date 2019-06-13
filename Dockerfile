FROM python:3.7-alpine

WORKDIR /usr/src/app
RUN apk update && \
    apk add zip

COPY source/ .

RUN pip install -r requirements.txt -t .

RUN zip -r9 /deployment.zip .