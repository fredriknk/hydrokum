import datetime
import socket
import time
import sqlite3
from sqlite3 import Error

# Your socket and database configuration here...
HOST = '10.0.20.3'  # Replace with your host
PORT = 51020  # Replace with your port

def create_connection():
    conn = None;
    try:
        conn = sqlite3.connect('my_database.sqlite') # Creates SQLite database file if it doesn't exist
        return conn
    except Error as e:
        print(e)

    return conn

def create_table():
    conn = create_connection()
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS data
                     (time text, N2O_ppm real, CO2_ppm real, CH4_ppm real, NH3_ppb real)''')
    except Error as e:
        print(e)
    finally:
        conn.close()

def insert_data(data):
    conn = create_connection()
    try:
        conn.execute("INSERT INTO data (time, N2O_ppm, CO2_ppm, CH4_ppm, NH3_ppb) VALUES (?, ?, ?, ?, ?)", data)
        conn.commit()
        conn.close()
    except Error as e:
        print(e)

def query_data(last_plotted_time=None, lim = 1000):
    conn = create_connection()
    cur = conn.cursor()

    if last_plotted_time is None:
        cur.execute(f"SELECT * FROM data ORDER BY time DESC LIMIT {lim}")
    else:
        cur.execute("SELECT * FROM data WHERE time > ? ORDER BY time ASC", (last_plotted_time,))

    rows = cur.fetchall()
    conn.close()

    return rows

# Create table if it doesn't exist
create_table()

# Inside your infinite loop
while True:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(b"_Meas_GetConc\r")
        data = s.recv(1024).decode('utf-8')

    values = data.strip().split(';')
    values_to_plot = [float(values[2]), float(values[7]), float(values[9]), float(values[12])]
    print(values)
    # Insert new data into the database
    insert_data([datetime.datetime.now()] + values_to_plot)

    # Sleep for one second
    time.sleep(5)
