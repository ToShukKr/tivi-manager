import os
import json
import logging
import requests
import subprocess
from flask_cors import CORS
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, render_template

logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s]: %(message)s')
logger = logging.getLogger('tivi')

TEMPLATE_DIR = os.path.join('/', 'app', 'templates')
STATIC_DIR = os.path.join('/', 'app','templates')
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
cors = CORS(app, resources={r"/*": {"origins": "*"}})

DATA_DIR = os.path.join("/", "data")
QUEUE_DIR = os.path.join(DATA_DIR, "queue")
IN_PROGRESS = os.path.join(DATA_DIR, "in_progress")

for dir in [QUEUE_DIR,IN_PROGRESS]:
    if not os.path.exists(dir):
        os.mkdir(dir)
