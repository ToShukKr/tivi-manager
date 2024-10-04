FROM python:3.12.3-slim-bookworm

RUN apt update && \
    apt install -y \
    libxml2-dev \
    libxslt1-dev \
    ffmpeg \
    aria2 \
    gcc

RUN pip3 install \
      requests==2.28.1 \
      retrying==1.3.3 \
      Flask-Cors==3.0.10 \
      flask==2.1.3 \
      bs4==0.0.1 \
      lxml==4.9.2 \
      supervisor==4.2.4

COPY ./config/ /

COPY ./app /app

WORKDIR /app

CMD /usr/local/bin/supervisord --nodaemon -c /etc/supervisor/supervisord.conf
