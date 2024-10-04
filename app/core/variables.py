import os
import subprocess
from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import json
from flask_cors import CORS
