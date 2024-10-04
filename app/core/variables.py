import os
import json
import requests
import subprocess
from flask_cors import CORS
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})
