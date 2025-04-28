# server.py
from flask import Flask, send_from_directory
import os

app = Flask(__name__)

@app.route('/models/<path:filename>')
def download_file(filename):
    return send_from_directory('models', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
