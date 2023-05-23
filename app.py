from flask import Flask, request, jsonify
from operator import itemgetter
from datetime import datetime, timedelta

from google.cloud import storage
from werkzeug.utils import secure_filename
import hashlib
import MySQLdb
import mimetypes
import os

import hashlib
import MySQLdb
import jwt

BUCKET_NAME = "dev-optikoe-bucket"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'optiqoe123'
    
# DEFINE THE DATABASE CREDENTIALS
db = MySQLdb.connect(
    user = 'root',
    # password = 'password',
    host = '127.0.0.1',
    port = 3306,
    database = "optikoe"
)

cur = db.cursor()
        
'''
1. POST /register (done)
2. POST /login (done)
3. POST /foto (done)
4. GET /user 
5. GET /toko (connect firebase)
7. POST /rating
9. GET /kacamata
11. GET /role

Dokumentasi API:
https://docs.google.com/document/d/1WQX2RLlHI9oH0Hki_tEWKwctzKtyUGKKlpKHLl1vbdY/edit#
'''

@app.route("/")
def home():
    return "Hello, Flask!"

@app.route("/register", methods = ['POST'])
def register():
    content = get_data_json(request)

    try: 
        # ambil values dari json nya
        name, email, password, confirmation_password, phone_number = itemgetter('name', 'email', 'password', 'confirmation_password', 'phone_number') (content) 
        
        # password mismatch
        if (password != confirmation_password):
            return {
                'status': 400,
                'message': 'Password doesn’t match'
            }
        id_user = hash_name(name)
    
        # hashing id_user
        currentDateTime = datetime.now()
        hashing = hashlib.md5((name + str(currentDateTime)).encode())
        id_user = hashing.hexdigest()
        
        # sql
        sql = "INSERT INTO users(id_user, nama, email, no_hp, password) VALUES (%s, %s, %s, %s, %s)"
        values = (id_user, name, email, password, phone_number)
        
        cur.execute(sql, values)
        db.commit()
    
    # kalau values json nya gaada
    except KeyError: 
        return {
          'status': 400,  
          'message': 'All data must be filled'
        }, 400
    
    # berhasil semuanya
    return {
        'status': 200,
        'message': 'Success'
    }, 200

@app.route("/foto", methods=['POST'])
def uploadFoto():
args = request.args.get('type')
pathFolder = ""

if args == 'profil':
    pathFolder = "foto-profil/"

if args == 'produk':
    pathFolder = "produk/"

if request.method == 'POST':
    file_upload = request.files['file']

    # Use os.path.splitext to split the file name and extension
    filename, file_ext = os.path.splitext(file_upload.filename)
    name_file_secured = (hashlib.md5(filename.encode())).hexdigest()

    if file_upload:
        upload = upload_to_gcs(file_upload, pathFolder + name_file_secured + file_ext)
        print(upload)
        if upload:
            return {
                'status': 200,
                'message': 'Success',
                'data': {
                    'folder': pathFolder, 
                    'filename': name_file_secured 
                }
            }, 200

        else:    
            return {
                'status': 400,
                'message': "File upload failed"
            }, 400

@app.route("/login", methods = ['POST'])
def login():
    content = get_data_json(request)
    try:
        # Ambil values dari JSON
        email, password = itemgetter('email', 'password')(content)

        # Ambil data dari SQL
        sql = "SELECT id_user, email, password FROM users WHERE email = %s"
        values = (email,)

        cur.execute(sql, values)
        user = cur.fetchone()

        if user:
            id_user, _, password_db = user
            # Memverifikasi password
            if password_db != password:
                return jsonify({'status': 401, 'message': 'Invalid email or password'}), 401

             # Generate token
            token_payload = {
                'id_user': id_user,
                'email': email,
                'exp': datetime.utcnow() + timedelta(hours=1)  # Token berlaku selama 1 jam
            }
            token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm='HS256')


            # Mengembalikan data pengguna
            response = {
                'status': 200,
                'message': 'Login successful',
                'data': {
                    'id_user': id_user,
                    'email': email,
                    'token': token
                }
            }
            return jsonify(response), 200
        else:
            return jsonify({'status': 400, 'message': 'Email not found'}), 400
        
    # Jika values JSON tidak ada
    except KeyError:
        return jsonify({'status': 400, 'message': 'All data must be filled'}), 400

@app.route("/user", methods=['GET'])
def get_users():
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({'status': 401, 'message': 'Invalid or missing bearer token'}), 401
    
    try:
        # Extract bearer token
        token = token.split("Bearer ")[1]
        
        # Verifikasi token
        token_payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        decoded_id_user = token_payload['id_user']

        # Fetch data user dari database
        sql = "SELECT id_user, nama, email, no_hp, id_role, id_bentuk_muka, path_foto, alamat FROM users"
        cur.execute(sql)
        users = cur.fetchall()

        if users:

            # tampilkan data semua user dalam array
            response_data = []
            for user in users:
                id_user, nama, email, no_hp, null, null, null, null = user
                user_data = {
                    'id_user': id_user,
                    'nama': nama,
                    'email': email,
                    'no_hp': no_hp,
                    'id_role': null,
                    'id_bentuk_muka': null,
                    'path_foto': null,
                    'alamat': null
                }
                response_data.append(user_data)

            # generate respons
            response = {
                'status': 200,
                'message': 'Success',
                'data': response_data
            }

            response_headers = {
                'Authorization': request.headers.get('Authorization')
            }
            return jsonify(response), 200, response_headers

        else:
            return jsonify({'status': 400, 'message': 'No users found'}), 400
    
    # apabila token expired
    except jwt.ExpiredSignatureError:
        return jsonify({'status': 401, 'message': 'Token has expired'}), 401
    
    # apabila token invalid
    except jwt.InvalidTokenError:
        return jsonify({'status': 401, 'message': 'Invalid token'}), 401


@app.route("/user/<id_user>", methods=['GET'])
def get_user_id(id_user):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'status': 401, 'message': 'Authorization token is missing'}), 401
    
    try:
        # Extract bearer token
        token = token.split("Bearer ")[1]

        # Verifikasi token
        token_payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        decoded_id_user = token_payload['id_user']

        # Check jika decode ID dari token sama dengan ID yang diminta
        if decoded_id_user != id_user:
            return jsonify({'status': 401, 'message': 'Invalid user ID'}), 401

        # Fetch data user dari database
        sql = "SELECT id_user, nama, email, no_hp, id_role, id_bentuk_muka, path_foto, alamat FROM users WHERE id_user = %s"
        values = (id_user,)

        cur.execute(sql, values)
        user = cur.fetchone()

        if user:
            id_user, nama, email, no_hp, id_role, id_bentuk_muka, path_foto, alamat = user
            # generate respons
            response = {
                'status': 200,
                'message': 'Success',
                'data': {
                    'id_user': id_user,
                    'nama': nama,
                    'email': email,
                    'no_hp': no_hp,
                    'id_role': id_role,
                    'id_bentuk_muka': id_bentuk_muka,
                    'path_foto': path_foto,
                    'alamat': alamat,

                }
            }
            return jsonify(response), 200
        else:
            return jsonify({'status': 400, 'message': 'User not found'}), 400
    
    # apabila token expired
    except jwt.ExpiredSignatureError:
        return jsonify({'status': 401, 'message': 'Token has expired'}), 401
    
    # apabila token invalid
    except jwt.InvalidTokenError:
        return jsonify({'status': 401, 'message': 'Invalid token'}), 401
        
    
@app.route("/toko", methods=["GET", "POST"])
def getToko():
    if request.method == "POST":
        return
    
    if request.method == "GET":
        return

@app.route("/toko/<id_toko>", methods=["GET"])
def getTokoById(id_toko):
    return id_toko

@app.route("/rating", methods=["GET", "POST"])
def rating():
    return

@app.route("/rating/<id_rating>", methods=["GET"])
def getRatingById(id_rating):
    return id_rating

@app.route("/kacamata", methods=["GET"])
def getKacamata():
    return

@app.route("/muka", methods=["GET"])
def getMuka():
    return

def get_data_json(req):
    content_type = req.headers.get('Content-Type')
    if (content_type == 'application/json'):
        json = req.json
        return json
    
def hash_name(name):
    # hashing id_user
    currentDateTime = datetime.now()
    hashing = hashlib.md5((name + str(currentDateTime)).encode())
    id_user = hashing.hexdigest()
    return id_user

def upload_to_gcs(file_data, destination_blob_name, bucket_name = BUCKET_NAME):
    # Create a client
    client = storage.Client.from_service_account_json('service_account.json')
    
    # Get the bucket
    bucket = client.get_bucket(bucket_name)
    
    # Create a blob object with the desired destination blob name
    blob = bucket.blob(destination_blob_name)
    
    # Set the content type based on file extension
    content_type, _ = mimetypes.guess_type(file_data.filename)
    blob.content_type = content_type
    
    # Upload the file data to the blob
    blob.upload_from_file(file_data)
    
    expiration = datetime.now() + timedelta(hours=1)
    signed_url = blob.generate_signed_url(expiration=expiration)
    return signed_url


if __name__ == '__main__':
    app.run(host = "localhost", port=8000, debug=True)