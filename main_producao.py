
from flask import Flask, request, jsonify
import os, json, time, requests
import redis
import urllib.parse

app = Flask(__name__)
CONFIG_URL = "https://raw.githubusercontent.com/kelissonvidal/painel-empresa/refs/heads/main/config.json"
