from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import mysql.connector
import os
import paramiko

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Konfigurasi Database MySQL
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'admin')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'ali123')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'client')
app.config['JWT_SECRET_KEY'] = "supersecretkey"

jwt = JWTManager(app)

# Koneksi ke Database
def get_db_connection():
    return mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )

# Konfigurasi MikroTik
MIKROTIK_HOST = os.getenv('MIKROTIK_HOST', '192.168.126.120')
MIKROTIK_USER = os.getenv('MIKROTIK_USER', 'admin')
MIKROTIK_PASS = os.getenv('MIKROTIK_PASS', '')

# def connect_to_mikrotik():
#     try:
#         ssh = paramiko.SSHClient()
#         ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#         ssh.connect(MIKROTIK_HOST, username=MIKROTIK_USER, password=MIKROTIK_PASS)
#         return ssh
#     except Exception as e:
#         raise Exception(f"Error connecting to MikroTik: {e}")

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    connection = get_db_connection()
    cursor = connection.cursor()
    query = "SELECT * FROM admin WHERE username = %s AND password = %s"
    cursor.execute(query, (username, password))
    user = cursor.fetchone()
    cursor.close()
    connection.close()

    if not user:
        return jsonify({"msg": "Username atau password salah!"}), 401

    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token)

@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

@app.route('/add_user', methods=['POST'])
def add_user():
    try:
        data = request.json
        nama, username, passwd, ip, alamat, notelp = data.values()
        
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = "INSERT INTO users (nama, username, passwd, ip, alamat, notelp) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(query, (nama, username, passwd, ip, alamat, notelp))
            connection.commit()
        return jsonify({"message": "User berhasil ditambahkan!"}), 201
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/get_users', methods=['GET'])
def get_users():
    try:
        connection = get_db_connection()
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
        return jsonify(users), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/update_user/<int:user_id>', methods=['PUT'])
def update_users(user_id):
    try:
        data = request.json
        connection = get_db_connection()

        with connection.cursor() as cursor:
            sql = """
                UPDATE users 
                SET nama=%s, username=%s, passwd=%s, ip=%s, alamat=%s, notelp=%s 
                WHERE id=%s
            """
            values = (data['nama'], data['username'], data['passwd'], data['ip'], data['alamat'], data['notelp'], user_id)
            cursor.execute(sql, values)
            connection.commit()

            socketio.emit('update_user')

        return jsonify({"message": "User berhasil diperbarui!"}), 200
    except mysql.connector.Error as err:
        return jsonify({"message": f"Error Database: {err}"}), 500
    
@app.route('/delete_user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
            connection.commit()
            socketio.emit('delete_user')
        return jsonify({"message": "User berhasil dihapus!"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/add_paket', methods=['POST'])
def add_paket():
    try:
        data = request.json
        nama, kecepatan, harga, masa_aktif = data.values()
        
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = "INSERT INTO paket (nama, kecepatan, harga, masa_aktif) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (nama, kecepatan, harga, masa_aktif))
            connection.commit()
        return jsonify({"message": "Paket berhasil ditambahkan!"}), 201
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/get_paket', methods=['GET'])
def get_paket():
    try:
        connection = get_db_connection()
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM paket")
            paket = cursor.fetchall()
        return jsonify(paket), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/update_paket/<int:paket_id>', methods=['PUT'])
def update_paket(paket_id):
    try:
        data = request.json
        connection = get_db_connection()

        with connection.cursor() as cursor:
            sql = """
                UPDATE paket 
                SET nama=%s, kecepatan=%s, harga=%s, masa_aktif=%s
                WHERE id=%s
            """
            values = (data['nama'], data['kecepatan'], data['harga'], data['masa_aktif'], paket_id)
            
            cursor.execute(sql, values)
            connection.commit()

            socketio.emit('update_paket')

        return jsonify({"message": "Paket berhasil diperbarui!"}), 200
    except mysql.connector.Error as err:
        return jsonify({"message": f"Error Database: {err}"}), 500

@app.route('/delete_paket/<int:paket_id>', methods=['DELETE'])
def delete_paket(paket_id):
    try:
        connection = get_db_connection()
        
        with connection.cursor() as cursor:
            sql = "DELETE FROM paket WHERE id=%s"
            cursor.execute(sql, (paket_id,))
            connection.commit()
            
            socketio.emit('delete_paket')
        
        return jsonify({"message": "Paket berhasil dihapus!"}), 200
    except mysql.connector.Error as err:
        return jsonify({"message": f"Error Database: {err}"}), 500

# Jalankan Flask
if __name__ == '__main__':
    app.run(host="10.3.3.120", debug=True)
