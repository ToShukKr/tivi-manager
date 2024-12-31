import os
import sys
import json
import time
import logging
import requests
import subprocess
import internetarchive
from time import sleep
from retrying import retry
from flask_cors import CORS
from bs4 import BeautifulSoup
from flask_apscheduler import APScheduler
from flask import Flask, request, jsonify, render_template

class Config:
    SCHEDULER_API_ENABLED = True

TEMPLATE_DIR = os.path.join('/', 'app', 'templates')
STATIC_DIR = os.path.join('/', 'app','templates')
DATA_DIR = os.path.join("/", "data")
QUEUE_DIR = os.path.join(DATA_DIR, "queue")
IN_PROGRESS = os.path.join(DATA_DIR, "in_progress")
CACHE_DIR = os.path.join("/", "cache")
LOGS_DIR = os.path.join(DATA_DIR, 'logs')
LOGS_APP_FILE = os.path.join(LOGS_DIR, 'tivi-manager.log')
MAX_QUEUE = os.getenv("MAX_QUEUE", 1)
DOWNLOAD_THREADS = 16
DOWNLOAD_THREAD_PREFIX_NAME = "download"
VIDEO_FILE_EXTENSION = '.mp4'

for dir in [QUEUE_DIR, IN_PROGRESS, LOGS_DIR, CACHE_DIR]:
    if not os.path.exists(dir):
        os.mkdir(dir)

logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s]: %(message)s', handlers=[logging.FileHandler(LOGS_APP_FILE), logging.StreamHandler()])
logger = logging.getLogger('tivi-manager')
