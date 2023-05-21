from flask import Flask, request, jsonify
from operator import itemgetter
from datetime import datetime, timedelta
import hashlib
import MySQLdb
import jwt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'optiqoe123'
    
def get_data_json(req):
    content_type = req.headers.get('Content-Type')
    if (content_type == 'application/json'):
        json = request.json
        return json

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
1. POST /register (bikin cadangan)
3. POST /foto 
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

if __name__ == '__main__':
    app.run(host = "localhost", port=8000, debug=True)