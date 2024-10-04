FROM python:3.12.3-slim-bookworm

RUN apt update && \
    apt install -y \
    ffmpeg \
    aria2

RUN pip3 install \
      requests==2.28.1 \
      retrying==1.3.3 \
      Flask-Cors \
      flask \
      bs4==0.0.1 \
      supervisor

COPY ./config/ /

COPY ./app /app

WORKDIR /app

CMD /usr/local/bin/supervisord --nodaemon -c /etc/supervisor/supervisord.conf
