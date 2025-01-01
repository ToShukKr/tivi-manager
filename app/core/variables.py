import os
import sys
import json
import glob
import time
import shutil
import random
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

FILMIX_URL = "https://filmix.my"
TEMPLATE_DIR = os.path.join('/', 'app', 'templates')
STATIC_DIR = os.path.join('/', 'app','templates')
DATA_DIR = os.path.join("/", "data")
QUEUE_DIR = os.path.join(DATA_DIR, "queue")
IN_PROGRESS = os.path.join(DATA_DIR, "in_progress")
CACHE_DIR = os.path.join("/", "cache")
UPLOAD_CACHE_DIR = os.path.join(DATA_DIR, "cache")
LOGS_DIR = os.path.join(DATA_DIR, 'logs')
LOGS_APP_FILE = os.path.join(LOGS_DIR, 'tivi-manager.log')
DOWNLOAD_THREADS = 16
DOWNLOAD_THREAD_PREFIX_NAME = "download"
CONVERT_THREAD_PREFIX_NAME = "convert"
VIDEO_FILE_EXTENSION = '.mp4'
BIN_FILE_EXTENSION = '.bin'
DEFAULT_QUALITY = '720p'
ARCHIVE_URL = 'https://archive.org'
METADATA_YT_FILE = os.path.join("/", 'metadata.json')

ARCHIVE_BUCKET_NAME = "tivi_tmp"
ARCHIVE_ACCESS_KEY_ID = "GRQdiTvvzzYvlipD"
ARCHIVE_SECRET_ACCESS_KEY = "x9b0S8iPZyEuC79d"

for dir in [QUEUE_DIR, IN_PROGRESS, LOGS_DIR, CACHE_DIR, UPLOAD_CACHE_DIR]:
    if not os.path.exists(dir):
        os.mkdir(dir)

logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s]: %(message)s', handlers=[logging.FileHandler(LOGS_APP_FILE), logging.StreamHandler()])
logger = logging.getLogger('tivi-manager')
