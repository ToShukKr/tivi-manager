FROM python:3.12.3-slim-bookworm

RUN apt update && \
    apt install -y \
    ffmpeg \
    aria2 \
    procps

RUN pip3 install \
      requests==2.28.1 \
      retrying==1.3.3 \
      Flask-Cors \
      flask \
      bs4==0.0.1 \
      Flask-APScheduler==1.13.1 \
      internetarchive==4.1.0

COPY ./app /app

WORKDIR /app

RUN ln -s /app/tivi-manager.py  /usr/bin/tivi-manager && \
    ln -s /app/tivi-queue.py  /usr/bin/tivi-queue

CMD tivi-manager
