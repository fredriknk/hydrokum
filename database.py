import datetime
import socket
import time
import sqlite3
from sqlite3 import Error
from typing import List, Tuple, Optional


class Database:
    def __init__(self, db_name: str):
        self.db_name = db_name

    def create_connection(self) -> Optional[sqlite3.Connection]:
        try:
            conn = sqlite3.connect(self.db_name)
            return conn
        except Error as e:
            print(e)
        return None

    def create_table(self) -> None:
        conn = self.create_connection()
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS data
                         (time text, N2O_ppm real, CO2_ppm real, CH4_ppm real, NH3_ppb real)''')

    def insert_data(self, data: List) -> None:
        conn = self.create_connection()
        with conn:
            conn.execute("INSERT INTO data (time, N2O_ppm, CO2_ppm, CH4_ppm, NH3_ppb) VALUES (?, ?, ?, ?, ?)", data)

    def query_data(self, last_plotted_time: Optional[str] = None, lim: int = 1000) -> List[Tuple]:
        conn = self.create_connection()
        with conn:
            cur = conn.cursor()
            if last_plotted_time is None:
                cur.execute(f"SELECT * FROM data ORDER BY time DESC LIMIT {lim}")
            else:
                cur.execute("SELECT * FROM data WHERE time > ? ORDER BY time ASC", (last_plotted_time,))
            return cur.fetchall()


def main():
    HOST = '10.0.20.3'
    PORT = 51020
    db = Database('my_database.sqlite')
    db.create_table()

    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(b"_Meas_GetConc\r")
            data = s.recv(1024).decode('utf-8')

        values = data.strip().split(';')
        values_to_plot = [float(values[2]), float(values[7]), float(values[9]), float(values[12])]
        print(values)

        # Insert new data into the database
        db.insert_data([str(datetime.datetime.now())] + values_to_plot)

        # Sleep for 5 seconds
        time.sleep(5)


if __name__ == "__main__":
    main()
