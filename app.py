from flask import Flask, request, redirect, session, send_from_directory, url_for, render_template, jsonify
import sqlite3
import bcrypt
import os
import cv2
import numpy as np
import uuid
from werkzeug.utils import secure_filename
from insightface.app import FaceAnalysis
from insightface.model_zoo.inswapper import INSwapper
from functools import wraps
import os
import urllib.request

MODEL_DIR = os.path.expanduser("~/.insightface/models/")
MODEL_PATH = os.path.join(MODEL_DIR, "inswapper_128.onnx")

# Make sure model folder exists
os.makedirs(MODEL_DIR, exist_ok=True)

# Download model if not exists
if not os.path.exists(MODEL_PATH):
    print("🔄 Downloading InsightFace model...")
    https://drive.usercontent.google.com/download?id=1krOLgjW2tAPaqV-Bw4YALz0xT5zlb5HF&export=download&authuser=0
    urllib.request.urlretrieve(url, MODEL_PATH)
    print("✅ Model downloaded!")

# Then load
from insightface.model_zoo.inswapper import INSwapper
swapper = INSwapper(MODEL_PATH)

app = Flask(__name__)


UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
face_app.prepare(ctx_id=0)
MODEL_DIR = os.path.expanduser("~/.insightface/models/")
swapper = INSwapper(os.path.join(MODEL_DIR, "inswapper_128.onnx"))

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def home():
    return redirect('/faceswap')

@app.route('/faceswap')
@login_required
def faceswap():
    return render_template("faceswap.html")

@app.route('/swap_faces', methods=['POST'])
@login_required
def swap_faces():
    photoA_list = request.files.getlist('photoA')
    photoB = request.files.get('photoB')
    strength = float(request.form.get('strength', 1))

    if not photoA_list or not photoB:
        return "Missing images", 400

    src_faces = []
    for file in photoA_list:
        filename = secure_filename(file.filename)
        src_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(src_path)
        img = cv2.imread(src_path)
        if img is not None:
            detected = face_app.get(img)
            if detected:
                src_faces.append(detected[0])

    tgt_filename = secure_filename(photoB.filename)
    tgt_path = os.path.join(UPLOAD_FOLDER, tgt_filename)
    photoB.save(tgt_path)
    tgt_img = cv2.imread(tgt_path)

    if tgt_img is None:
        return "Target image not readable", 400

    tgt_faces = face_app.get(tgt_img)
    if not src_faces or not tgt_faces:
        return "No faces detected", 400

    output = tgt_img.copy()
    for i, tgt_face in enumerate(tgt_faces):
        src_face = src_faces[i % len(src_faces)]
        output = swapper.get(output, tgt_face, src_face, paste_back=True)

    result_filename = f"result_{uuid.uuid4().hex}.jpg"
    result_path = os.path.join(RESULT_FOLDER, result_filename)
    cv2.imwrite(result_path, output)

    conn = sqlite3.connect("users.db")
    conn.execute("CREATE TABLE IF NOT EXISTS history (email TEXT, result_path TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    conn.execute("INSERT INTO history (email, result_path) VALUES (?, ?)", (session['user_email'], result_filename))
    conn.commit()
    conn.close()

    return redirect(url_for('gallery'))

@app.route('/gallery')
@login_required
def gallery():
    return render_template("gallery.html")

@app.route('/api/gallery')
@login_required
def api_gallery():
    page = int(request.args.get('page', 1))
    per_page = 6
    offset = (page - 1) * per_page

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT result_path, timestamp FROM history WHERE email = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?", (session['user_email'], per_page, offset))
    results = cur.fetchall()
    conn.close()

    data = [{
        'path': path,
        'timestamp': timestamp
    } for path, timestamp in results]

    return jsonify(data)

@app.route('/preview')
@login_required
def preview():
    filename = request.args.get('file')
    return render_template("preview.html", filename=filename)

@app.route('/delete_result', methods=['POST'])
@login_required
def delete_result():
    path = request.form.get('path')
    try:
        os.remove(os.path.join(RESULT_FOLDER, os.path.basename(path)))
    except:
        pass
    conn = sqlite3.connect("users.db")
    conn.execute("DELETE FROM history WHERE email = ? AND result_path = ?", (session['user_email'], path))
    conn.commit()
    conn.close()
    return '', 204

@app.route('/results/<filename>')
def serve_result(filename):
    return send_from_directory(RESULT_FOLDER, filename)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    email = request.form['email']
    password = request.form['password']
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    conn = sqlite3.connect("users.db")
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT)")
        conn.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed))
        conn.commit()
    except sqlite3.IntegrityError:
        return "Email already registered"
    finally:
        conn.close()

    session['user_email'] = email
    return redirect('/faceswap')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    conn.close()

    if row and bcrypt.checkpw(password.encode(), row[0]):
        session['user_email'] = email
        return redirect('/faceswap')
    else:
        return "Invalid login"

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect('/login')
    
# === Database Initialization ===
def init_db():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            email TEXT,
            result_path TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 4242))  # fallback for local
    app.run(debug=True, host='0.0.0.0', port=port)

