from flask import Flask, request
from operator import itemgetter
from datetime import datetime
import hashlib
import MySQLdb

app = Flask(__name__)
    
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
        name, email, password, confirmation_password, phone_number = itemgetter('name', 'email', 'password', 'confirmation_password', 'phone_number') (content) 
        
        if (password != confirmation_password):
            return {
                'status': 400,
                'message': 'Password doesn’t match'
            }
    
        currentDateTime = datetime.now()
        hashing = hashlib.md5((name + currentDateTime).encode())
        id_user = hashing.hexdigest()
        
        print (id_user)
        sql = "INSERT INTO users(id_user, nama, email, no_hp, password) VALUES (%s, %s, %s, %s, %s)"
        values = (id_user, name, email, password, phone_number)
        
        cur.execute(sql, values)
        db.commit()
            
    except KeyError: 
        return {
          'status': 400,  
          'message': 'All data must be filled'
        }, 400
        
    return {
        'status': 200,
        'message': 'Success'
    }, 200

if __name__ == '__main__':
    app.run(host = "localhost", port=8000, debug=True)