from flask import Flask, request, jsonify
from operator import itemgetter
from datetime import datetime, timedelta
from functools import wraps
from google.cloud import storage
import hashlib
import MySQLdb
import mimetypes
import os
import jwt

BUCKET_NAME = "dev-optikoe-bucket"

app = Flask(__name__)
app.config["SECRET_KEY"] = "optiqoe123"

# DEFINE THE DATABASE CREDENTIALS
db = MySQLdb.connect(
    user="root",
    # password = 'password',
    host="127.0.0.1",
    port=3306,
    database="optikoe",
)

cur = db.cursor()


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return (
                jsonify({"status": 401, "message": "Invalid or missing bearer token"}),
                401,
            )

        try:
            # Extract bearer token
            token = token.split("Bearer ")[1]

            # Verifikasi token
            token_payload = jwt.decode(
                token, app.config["SECRET_KEY"], algorithms=["HS256"]
            )
            decoded_id_user = token_payload["id_user"]
            decoded_id_toko = token_payload["id_toko"]

            # Pass the decoded user ID to the decorated function
            return f(decoded_id_user, decoded_id_toko, *args, **kwargs)

        # apabila token expired
        except jwt.ExpiredSignatureError:
            return jsonify({"status": 401, "message": "Token has expired"}), 401

        # apabila token invalid
        except jwt.InvalidTokenError:
            return jsonify({"status": 401, "message": "Invalid token"}), 401

    return decorated


"""
1. POST /register (done)
2. POST /login (done)
3. POST /foto (done)
4. GET /user (done)
5. GET /toko (done)
7. POST /rating (done)
9. GET /kacamata
11. GET /role

Dokumentasi API:
https://docs.google.com/document/d/1WQX2RLlHI9oH0Hki_tEWKwctzKtyUGKKlpKHLl1vbdY/edit#
"""


@app.route("/")
def home():
    return "Hello, Flask!"


@app.route("/register", methods=["POST"])
def register():
    content = get_data_json(request)

    try:
        # ambil values dari json nya
        name, email, password, confirmation_password, phone_number = itemgetter(
            "name", "email", "password", "confirmation_password", "phone_number"
        )(content)

        # password mismatch
        if password != confirmation_password:
            return {"status": 400, "message": "Password doesn’t match"}
        id_user = hash_name(name)

        sql = "SELECT * FROM users WHERE email = %s"
        values = [email]

        cur.execute(sql, values)
        email_duplicated = cur.fetchall()

        if email_duplicated:
            return jsonify({"status": 400, "message": "Email already registered"}), 400

        else:
            # INSERT DATA USER
            sql = "INSERT INTO users(id_user, nama, email, no_hp, password) VALUES (%s, %s, %s, %s, %s)"
            values = (id_user, name, email, password, phone_number)

            cur.execute(sql, values)
            db.commit()

    # kalau values json nya gaada
    except KeyError:
        return {"status": 400, "message": "All data must be filled"}, 400

    # berhasil semuanya
    return {"status": 200, "message": "Success"}, 200


@app.route("/foto", methods=["POST"])
def uploadFoto():
    args = request.args.get("type")
    pathFolder = ""

    if args == "profil":
        pathFolder = "foto-profil/"

    if args == "produk":
        pathFolder = "produk/"

    if request.method == "POST":
        file_upload = request.files["file"]

        if file_upload:
            # Use os.path.splitext to split the file name and extension
            filename, file_ext = os.path.splitext(file_upload.filename)
            name_file_secured = (hashlib.md5(filename.encode())).hexdigest()
            
            upload = upload_to_gcs(
                file_upload, pathFolder + name_file_secured + file_ext
            )
            print(upload)
            if upload:
                return {
                    "status": 200,
                    "message": "Success",
                    "data": {"folder": pathFolder, "filename": name_file_secured},
                }

            else:
                return {"status": 400, "message": "File upload failed"}


@app.route("/login", methods=["POST"])
def login():
    content = get_data_json(request)
    try:
        # Ambil values dari JSON
        email, password = itemgetter("email", "password")(content)

        # Ambil data dari SQL
        sql = "SELECT id_user, id_role, email, password FROM users WHERE email = %s"
        values = (email,)

        cur.execute(sql, values)
        user = cur.fetchone()

        if user:
            id_user, id_role, _, password_db = user
            id_toko = None

            # Memverifikasi password
            if password_db != password:
                return (
                    jsonify({"status": 401, "message": "Invalid email or password"}),
                    401,
                )

            # Generate token
            token_payload = {
                "id_user": id_user,
                "id_toko": id_toko,
                "email": email,
                "exp": datetime.utcnow() + timedelta(hours=24)
                # Token berlaku selama 24 jam
            }

            # Seller
            if id_role == 2:
                sql = "SELECT id_toko, tanggal_pendaftaran FROM toko WHERE id_user = %s"
                values = [id_user]

                cur.execute(sql, values)
                row_id_toko = cur.fetchone()

                # memeriksa jika row_id_toko not None
                if row_id_toko is not None:
                    id_toko, _ = row_id_toko
                    print(id_toko)

                    token_payload["id_toko"] = id_toko

            token = jwt.encode(
                token_payload, app.config["SECRET_KEY"], algorithm="HS256"
            )

            # Mengembalikan data pengguna
            response = {
                "status": 200,
                "message": "Login successful",
                "data": {
                    "id_user": id_user,
                    "id_toko": id_toko,
                    "email": email,
                    "token": token,
                },
            }

            if id_role == 2:
                response["data"]["id_toko"] = id_toko

            return jsonify(response), 200
        else:
            return jsonify({"status": 400, "message": "Invalid email or password"}), 400

    # Jika values JSON tidak ada
    except KeyError:
        return jsonify({"status": 400, "message": "All data must be filled"}), 400


@app.route("/user", methods=["GET"])
@token_required
def get_users(decoded_id_user, decoded_id_toko):
    try:
        # Fetch data user dari database
        sql = "SELECT id_user, nama, email, no_hp, id_role, id_bentuk_muka, path_foto, alamat FROM users"
        cur.execute(sql)
        users = cur.fetchall()

        if users:
            # tampilkan data semua user dalam array
            response_data = []
            for user in users:
                (
                    id_user,
                    nama,
                    email,
                    no_hp,
                    id_role,
                    id_bentuk_muka,
                    path_foto,
                    alamat,
                ) = user
                user_data = {
                    "id_user": id_user,
                    "nama": nama,
                    "email": email,
                    "no_hp": no_hp,
                    "id_role": id_role,
                    "id_bentuk_muka": id_bentuk_muka,
                    "path_foto": path_foto,
                    "alamat": alamat,
                }
                response_data.append(user_data)

            # generate respons
            response = {"status": 200, "message": "Success", "data": response_data}

            response_headers = {"Authorization": request.headers.get("Authorization")}
            return jsonify(response), 200, response_headers

        else:
            return jsonify({"status": 400, "message": "No users found"}), 400

    # apabila server error
    except:
        return jsonify({"status": 500, "message": "Internal Server Error"}), 500


@app.route("/user/<id_user>", methods=["GET"])
@token_required
def get_user_id(decoded_id_user, decoded_id_toko, id_user):
    try:
        # Fetch data user dari database
        sql = "SELECT id_user, nama, email, no_hp, id_role, id_bentuk_muka, path_foto, alamat FROM users WHERE id_user = %s"
        values = (id_user,)

        cur.execute(sql, values)
        user = cur.fetchone()

        if user:
            (
                id_user,
                nama,
                email,
                no_hp,
                id_role,
                id_bentuk_muka,
                path_foto,
                alamat,
            ) = user
            # generate respons
            response = {
                "status": 200,
                "message": "Success",
                "data": {
                    "id_user": id_user,
                    "nama": nama,
                    "email": email,
                    "no_hp": no_hp,
                    "id_role": id_role,
                    "id_bentuk_muka": id_bentuk_muka,
                    "path_foto": path_foto,
                    "alamat": alamat,
                },
            }
            return jsonify(response), 200
        else:
            return jsonify({"status": 400, "message": "User not found"}), 400
    # apabila server error
    except:
        return jsonify({"status": 500, "message": "Internal Server Error"}), 500


@app.route("/user/role/<role>", methods=["GET"])
@token_required
def get_user_role(decoded_id_user, id_user, role):
    try:
        # Fetch data user dari database
        sql = """
        SELECT u.id_user, u.nama, u.email, u.no_hp, u.id_role, u.id_bentuk_muka, u.path_foto, u.alamat
        FROM users u
        INNER JOIN roles r ON  u.id_role = r.id_role
        WHERE r.nama_role = %s
        """
        values = (role,)
        cur.execute(sql, values)
        users = cur.fetchall()

        if users:
            # tampilkan data semua user dalam array
            response_data = []
            for user in users:
                (
                    id_user,
                    nama,
                    email,
                    no_hp,
                    id_role,
                    id_bentuk_muka,
                    path_foto,
                    alamat,
                ) = user
                user_data = {
                    "id_user": id_user,
                    "nama": nama,
                    "email": email,
                    "no_hp": no_hp,
                    "id_role": id_role,
                    "id_bentuk_muka": id_bentuk_muka,
                    "path_foto": path_foto,
                    "alamat": alamat,
                }
                response_data.append(user_data)

            # generate respons
            response = {"status": 200, "message": "Success", "data": response_data}

            response_headers = {"Authorization": request.headers.get("Authorization")}
            return jsonify(response), 200, response_headers
        else:
            return (
                jsonify({"status": 400, "message": "No users in that role found"}),
                400,
            )

    # apabila server error
    except:
        return jsonify({"status": 500, "message": "Internal Server Error"}), 500


@app.route("/user/muka/<id_bentuk_muka>", methods=["GET"])
@token_required
def get_user_face(decoded_id_user, id_user, id_bentuk_muka):
    try:
        # Fetch data user dari database
        sql = "SELECT id_user, nama, email, no_hp, id_role, id_bentuk_muka, path_foto, alamat FROM users WHERE id_bentuk_muka = %s"
        values = (id_bentuk_muka,)
        cur.execute(sql, values)
        users = cur.fetchall()

        if users:
            # tampilkan data semua user dalam array
            response_data = []
            for user in users:
                (
                    id_user,
                    nama,
                    email,
                    no_hp,
                    id_role,
                    id_bentuk_muka,
                    path_foto,
                    alamat,
                ) = user
                user_data = {
                    "id_user": id_user,
                    "nama": nama,
                    "email": email,
                    "no_hp": no_hp,
                    "id_role": id_role,
                    "id_bentuk_muka": id_bentuk_muka,
                    "path_foto": path_foto,
                    "alamat": alamat,
                }
                response_data.append(user_data)

            # generate respons
            response = {"status": 200, "message": "Success", "data": response_data}

            response_headers = {"Authorization": request.headers.get("Authorization")}
            return jsonify(response), 200, response_headers
        else:
            return (
                jsonify({"status": 400, "message": "No users in that type face found"}),
                400,
            )

    # apabila server error
    except:
        return jsonify({"status": 500, "message": "Internal Server Error"}), 500


@app.route("/toko", methods=["POST", "PATCH", "GET"])
@token_required
def getToko(decoded_id_user, decoded_id_toko):
    id_user = decoded_id_user
    content = get_data_json(request)

    if request.method == "POST":
        try:
            # ambil values dari json nya
            nama_toko, deskripsi = itemgetter("nama_toko", "deskripsi")(content)

            id_toko = hash_name(nama_toko)

            sql = "INSERT INTO toko(id_toko, nama_toko, id_user, deskripsi) VALUES(%s, %s, %s, %s)"
            values = (id_toko, nama_toko, id_user, deskripsi)

            cur.execute(sql, values)
            db.commit()

        # kalau values json nya gaada
        except KeyError:
            return {"status": 400, "message": "All data must be filled"}, 400

        # berhasil semuanya
        return {"status": 200, "message": "Success", "data": {"id_toko": id_toko}}, 200

    if request.method == "PATCH":
        id_toko = decoded_id_toko
        try:
            # ambil values dari json nya
            nama_toko, deskripsi, path_foto = itemgetter(
                "nama_toko", "deskripsi", "path_foto"
            )(content)

            id_toko = hash_name(nama_toko)

            sql = "UPDATE toko SET nama_toko = %s, deskripsi = %s, path_foto = %s WHERE id_toko = %s"
            values = (nama_toko, deskripsi, path_foto, id_toko)

            cur.execute(sql, values)
            db.commit()

        # kalau values json nya gaada
        except KeyError:
            return {"status": 400, "message": "All data must be filled"}, 400

        # berhasil semuanya
        return {
            "status": 200,
            "message": "Success",
        }, 200

    if request.method == "GET":
        sql = "SELECT id_toko, nama_toko, path_foto, rating, id_user, deskripsi, tanggal_pendaftaran FROM toko"

        cur.execute(sql)
        semua_toko = cur.fetchall()

        if semua_toko:
            response_data = []

            for toko in semua_toko:
                (
                    id_toko,
                    nama_toko,
                    path_foto,
                    rating,
                    id_user,
                    deskripsi,
                    tanggal_pendaftaran,
                ) = toko
                data_toko = {
                    "id_toko": id_toko,
                    "nama_toko": nama_toko,
                    "path_foto": path_foto,
                    "rating": rating,
                    "id_user": id_user,
                    "deskripsi": deskripsi,
                    "tanggal_pendaftaran": tanggal_pendaftaran,
                }
                response_data.append(data_toko)

            return {"status": 200, "message": "Success", "data": response_data}, 200

        else:
            return {"status": "400", "message": "Toko not found", "data": None}, 400


@app.route("/toko/<id_toko>", methods=["GET"])
@token_required
def getTokoById(decoded_id_user, decoded_id_toko, id_toko):
    sql = "SELECT * FROM toko WHERE id_toko = %s"
    values = [id_toko]

    cur.execute(sql, values)
    toko = cur.fetchall()

    print(toko)

    if toko:
        response_data = []

        (
            id_toko,
            nama_toko,
            path_foto,
            rating,
            id_user,
            deskripsi,
            tanggal_pendaftaran,
        ) = toko[0]
        data_toko = {
            "id_toko": id_toko,
            "nama_toko": nama_toko,
            "path_foto": path_foto,
            "rating": rating,
            "id_user": id_user,
            "deskripsi": deskripsi,
            "tanggal_pendaftaran": tanggal_pendaftaran,
        }

        response_data.append(data_toko)

        return (
            jsonify({"status": 200, "message": "Success", "data": response_data}),
            200,
        )

    else:
        return (
            jsonify({"status": "400", "message": "Data not found", "data": None}),
            400,
        )

@app.route("/beli", methods=["POST"])
@token_required
def beliProduk(decoded_id_user, decoded_id_toko):
    id_user = decoded_id_user
    id_toko = decoded_id_toko
    content = get_data_json(request)

    try:
            # Ambil values dari JSON
            id_produk, jumlah_produk, = itemgetter(
                "id_produk", "jumlah_produk")(content)

            # Memeriksa apakah pengguna memiliki peran user (id_role=1)
            sql = "SELECT id_role FROM users WHERE id_user = %s"
            values = (id_user,)
            cur.execute(sql, values)
            result = cur.fetchone()

            if result and result[0] == 1:
                # Menjalankan query INSERT untuk beli produk ke database
                sql = """
                    INSERT INTO history (id_user, id_produk, jumlah_produk, id_status)
                    SELECT u.id_user, p.id_produk, %s, %s
                    FROM users u, produk p
                    WHERE u.id_user = %s
                    AND p.id_produk = %s;
                    
                    UPDATE produk
                    SET stok = stok - %s
                    WHERE id_produk = %s;
                """
                
                values = (
                    jumlah_produk,
                    0,  # Set id_status to 0
                    id_user,
                    id_produk,
                    jumlah_produk,
                    id_produk
                )
                cur.execute(sql, values)

                # Konsumsi set hasil dari statement pertama    
                cur.nextset()

                # Commit perubahan ke database
                db.commit()

                # Berhasil semuanya
                return (
                    jsonify(
                        {
                            "status": 200,
                            "message": "Success to Buy Product",
                            "data": {"id_product": id_produk},
                        }
                    ),
                    200,
                )
            else:
                return (
                    jsonify(
                        {
                            "status": 403,
                            "message": "Only users can access this feature",
                        }
                    ),
                    403,
                )

        # Kalau values JSON tidak ada
    except TypeError:
            return jsonify({"status": 400, "message": "All data must be filled"}), 400

    

@app.route("/rating", methods=["GET", "POST"])
@token_required
def rating(decoded_id_user, decoded_id_toko):
    if request.method == "GET":
        sql = "SELECT * FROM rating"
        cur.execute(sql)

        rating = cur.fetchall()
        if rating:
            response_data = []

            for oneRating in rating:
                (
                    id_rating,
                    id_user,
                    id_produk,
                    nilai_rating,
                    komentar,
                    tanggal,
                ) = oneRating

                data_rating = {
                    "id_rating": id_rating,
                    "id_user": id_user,
                    "id_produk": id_produk,
                    "nilai_rating": nilai_rating,
                    "komentar": komentar,
                    "tanggal": tanggal,
                }

                response_data.append(data_rating)

            return (
                jsonify({"status": 200, "message": "Success", "data": response_data}),
                200,
            )

        else:
            return (
                jsonify({"status": 400, "message": "Data not found", "data": None}),
                400,
            )

    if request.method == "POST":
        content = get_data_json(request)

        try:
            # ambil values dari json nya
            id_produk, nilai_rating, komentar = itemgetter(
                "id_produk", "nilai_rating", "komentar"
            )(content)

            id_rating = hash_name(id_produk + decoded_id_user)

            sql = "INSERT INTO rating(id_rating, id_user, id_produk, nilai_rating, komentar) VALUES (%s, %s, %s, %s, %s)"
            values = [id_rating, decoded_id_user, id_produk, nilai_rating, komentar]

            try:
                cur.execute(sql, values)

                if cur:
                    db.commit()

                    sql_select_toko = "SELECT toko.id_toko FROM toko JOIN produk ON toko.id_toko = produk.id_toko WHERE id_produk = %s"
                    values_select_toko = [id_produk]

                    cur.execute(sql_select_toko, values_select_toko)
                    id_toko = cur.fetchone()

                    if id_toko:
                        # Update Rating Toko
                        sql_update_rating = """
                            UPDATE toko 
                            SET rating =  (SELECT AVG(rating.nilai_rating) FROM rating  
                                            JOIN produk ON produk.id_produk = rating.id_produk 
                                            WHERE id_toko = %s)

                            WHERE id_toko = %s
                        """
                        values_update_rating = [id_toko, id_toko]

                        try:
                            cur.execute(sql_update_rating, values_update_rating)
                            db.commit()

                            return jsonify({"status": 200, "message": "Success"}), 200

                        except:
                            return (
                                jsonify({"status": 500, "message": "Server error"}),
                                500,
                            )

                else:
                    return jsonify({"status": 500, "message": "Server error"}), 500

            # Foreign Key Error: jika produk tidak ditemukan
            except MySQLdb.IntegrityError:
                return jsonify({"status": "404", "message": "Product not found"}), 404

            finally:
                cur.close()

        # Jika values JSON tidak ada
        except KeyError:
            return jsonify({"status": 400, "message": "All data must be filled"}), 400

        return


@app.route("/rating/<id_rating>", methods=["GET"])
@token_required
def getRatingById(decoded_id_user, decoded_id_token, id_rating):
    if request.method == "GET":
        sql = "SELECT * FROM rating WHERE id_rating = %s"
        values = [id_rating]
        cur.execute(sql, values)

        rating = cur.fetchall()
        if rating:
            response_data = []

            for oneRating in rating:
                (
                    id_rating,
                    id_user,
                    id_produk,
                    nilai_rating,
                    komentar,
                    tanggal,
                ) = oneRating

                data_rating = {
                    "id_rating": id_rating,
                    "id_user": id_user,
                    "id_produk": id_produk,
                    "nilai_rating": nilai_rating,
                    "komentar": komentar,
                    "tanggal": tanggal,
                }

                response_data.append(data_rating)

            return (
                jsonify({"status": 200, "message": "Success", "data": response_data}),
                200,
            )

        else:
            return (
                jsonify({"status": 400, "message": "Data not found", "data": None}),
                400,
            )

@app.route("/produk", methods=["POST"])
@token_required
def create_produk(decoded_id_user, decoded_id_toko):
    id_user = decoded_id_user
    id_toko = decoded_id_toko
    content = get_data_json(request)
    
    if request.method == "POST":
        if id_toko is None:
            return jsonify({
                'status': 401,
                'message': "UNAUTHORIZED"
            }), 401
        
        try:
            # Ambil values dari JSON
            nama_produk, harga, deskripsi, stok = itemgetter(
                "nama_produk", "harga", "deskripsi", "stok"
            )(content)

            id_produk = hash_name(nama_produk)

            # Memeriksa apakah pengguna memiliki peran penjual (id_role=2)
            sql = "SELECT id_role FROM users WHERE id_user = %s"
            values = (id_user,)
            cur.execute(sql, values)
            result = cur.fetchone()

            if result and result[0] == 2:
                # Menjalankan query INSERT untuk menyimpan produk ke database
                sql = "INSERT INTO produk (id_produk, id_toko, nama_produk, id_bentuk_kacamata, harga, deskripsi, stok, is_active) VALUES (%s, (SELECT id_toko FROM toko WHERE id_toko = %s), %s, %s, %s, %s, %s, %s)"
                values = (
                    id_produk,
                    id_toko,
                    nama_produk,
                    None,
                    harga,
                    deskripsi,
                    stok,
                    1,
                )
                cur.execute(sql, values)

                # Commit perubahan ke database
                db.commit()

                # Berhasil semuanya
                return (
                    jsonify(
                        {
                            "status": 200,
                            "message": "Product has been added",
                            "data": {"id_product": id_produk},
                        }
                    ),
                    200,
                )
            else:
                return (
                    jsonify(
                        {
                            "status": 403,
                            "message": "Only sellers can access this feature",
                        }
                    ),
                    403,
                )

        # Kalau values JSON tidak ada
        except TypeError:
            return jsonify({"status": 400, "message": "All data must be filled"}), 400
@app.route("/produk", methods=["GET"])
def getProduk():
    if request.method == "GET":
        sql = "SELECT id_produk, id_toko, nama_produk, id_bentuk_kacamata, harga, deskripsi, stok, is_active FROM produk"

        cur.execute(sql)
        semua_produk = cur.fetchall()

        if semua_produk:
            response_data = []

            for produk in semua_produk:
                (
                    id_produk,
                    id_toko,
                    nama_produk,
                    id_bentuk_kacamata,
                    harga,
                    deskripsi,
                    stok,
                    is_active,
                ) = produk
                data_produk = {
                    "id_produk": id_produk,
                    "id_toko": id_toko,
                    "nama_produk": nama_produk,
                    "id_bentuk_kacamata": id_bentuk_kacamata,
                    "harga": harga,
                    "deskripsi": deskripsi,
                    "stok": stok,
                    "is_active": is_active,
                }
                response_data.append(data_produk)

            return {"status": 200, "message": "Success", "data": response_data}, 200

        else:
            return {"status": "400", "message": "Product not found", "data": None}, 400

@app.route("/produk/<id_produk>", methods=["GET"])
def get_produk_id(id_produk):
    try:
        # Fetch data user dari database
        sql = "SELECT id_produk, id_toko, nama_produk, id_bentuk_kacamata, harga, deskripsi, stok, is_active FROM produk WHERE id_produk = %s"
        values = [id_produk]
        cur.execute(sql, values)

        produk = cur.fetchall()
        if produk:
            response_data = []

            for data_produk in produk:
                (
                    id_produk,
                    id_toko,
                    nama_produk,
                    id_bentuk_kacamata,
                    harga,
                    deskripsi,
                    stok,
                    is_active,
                ) = data_produk

                result_produk = {
                    "id_produk": id_produk,
                    "id_toko": id_toko,
                    "nama_produk": nama_produk,
                    "id_bentuk_kacamata": id_bentuk_kacamata,
                    "harga": harga,
                    "deskripsi": deskripsi,
                    "stok": stok,
                    "is_active": is_active,
                }

                response_data.append(result_produk)

            return (
                jsonify({"status": 200, "message": "Success", "data": response_data}),
                200,
            )
        else:
            return (
                jsonify({"status": 400, "message": "Data not found", "data": None}),
                400,
            )
    # apabila server error
    except:
        return jsonify({"status": 500, "message": "Internal Server Error"}), 500

@app.route("/produk/toko/<id_toko>", methods=["GET"])
def get_produk_by_toko(id_toko):
    try:
        # Fetch data user dari database
        sql = "SELECT id_produk, id_toko, nama_produk, id_bentuk_kacamata, harga, deskripsi, stok, is_active FROM produk WHERE id_toko = %s"
        values = [id_toko]
        cur.execute(sql, values)

        produk = cur.fetchall()
        if produk:
            response_data = []

            for data_produk in produk:
                (
                    id_produk,
                    id_toko,
                    nama_produk,
                    id_bentuk_kacamata,
                    harga,
                    deskripsi,
                    stok,
                    is_active,
                ) = data_produk

                result_produk = {
                    "id_produk": id_produk,
                    "id_toko": id_toko,
                    "nama_produk": nama_produk,
                    "id_bentuk_kacamata": id_bentuk_kacamata,
                    "harga": harga,
                    "deskripsi": deskripsi,
                    "stok": stok,
                    "is_active": is_active,
                }

                response_data.append(result_produk)

            return (
                jsonify({"status": 200, "message": "Success", "data": response_data}),
                200,
            )
        else:
            return (
                jsonify({"status": 400, "message": "Data not found", "data": None}),
                400,
            )
    # apabila server error
    except:
        return jsonify({"status": 500, "message": "Internal Server Error"}), 500


@app.route("/kacamata", methods=["GET"])
def getKacamata():
    sql = "SELECT * FROM bentuk_kacamata"
    cur.execute(sql)

    rows = cur.fetchall()

    if rows:
        response_data = []

        for row in rows:
            (id_bentuk_kacamata, bentuk_kacamata) = row

            data_kacamata = {
                "id_bentuk_kacamata": id_bentuk_kacamata,
                "bentuk_kacamata": bentuk_kacamata,
            }

            response_data.append(data_kacamata)

        return (
            jsonify({"status": 200, "message": "Success", "data": response_data}),
            200,
        )

    else:
        return (
            jsonify({"status": 400, "message": "Data not found", "data": None}),
            400,
        )


@app.route("/role", methods=["GET"])
def getRole():
    sql = "SELECT * FROM roles"
    cur.execute(sql)

    rows = cur.fetchall()

    if rows:
        response_data = []

        for row in rows:
            (id_role, nama_role) = row

            data_role = {"id_role": id_role, "nama_role": nama_role}

            response_data.append(data_role)

        return (
            jsonify({"status": 200, "message": "Success", "data": response_data}),
            200,
        )

    else:
        return (
            jsonify({"status": 400, "message": "Data not found", "data": None}),
            400,
        )


@app.route("/muka", methods=["GET"])
def getMuka():
    sql = "SELECT * FROM bentuk_muka"
    cur.execute(sql)

    rows = cur.fetchall()

    if rows:
        response_data = []

        for row in rows:
            (id_bentuk_muka, bentuk_muka) = row

            data_muka = {"id_bentuk_muka": id_bentuk_muka, "bentuk_muka": bentuk_muka}

            response_data.append(data_muka)

        return (
            jsonify({"status": 200, "message": "Success", "data": response_data}),
            200,
        )

    else:
        return (
            jsonify({"status": 400, "message": "Data not found", "data": None}),
            400,
        )


def get_data_json(req):
    content_type = req.headers.get("Content-Type")
    if content_type == "application/json":
        json = req.json
        return json


def hash_name(name):
    # hashing id_user
    currentDateTime = datetime.now()
    hashing = hashlib.md5((name + str(currentDateTime)).encode())
    id_user = hashing.hexdigest()
    return id_user


def upload_to_gcs(file_data, destination_blob_name, bucket_name=BUCKET_NAME):
    # Create a client
    client = storage.Client.from_service_account_json("service_account.json")

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


if __name__ == "__main__":
    app.run(host="localhost", port=8000, debug=True)
