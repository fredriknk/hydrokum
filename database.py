import datetime
import socket
import time
import sqlite3
from sqlite3 import Error
from typing import List, Tuple, Optional, Any


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
            conn.execute('''CREATE TABLE IF NOT EXISTS plc_history
                         (time text, ip_address text, event text)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS status_history
                         (time text, ip_address text, status int)''')

    def insert_status_change(self, data: List) -> None:
        conn = self.create_connection()
        if conn is None:
            self.logger.error("Database connection failed for status change.")
            return
        try:
            with conn:
                conn.execute("INSERT INTO status_history (time, ip_address, status) VALUES (?, ?, ?)", data)
        except Error as e:
            self.logger.error(f"Failed to insert status change: {e}")
    def insert_plc_history(self, data: List) -> None:
        conn = self.create_connection()
        if conn is None:
            self.logger.error("Database connection failed for history write.")
            return
        try:
            with conn:
                conn.execute("INSERT INTO plc_history (time, ip_address, event) VALUES (?, ?, ?)", data)
        except Error as e:
            self.logger.error(f"Failed to insert history: {e}")

    def insert_data(self, data: List) -> None:
        conn = self.create_connection()
        if conn is None:
            self.logger.error("Database connection failed for data write.")
            return
        try:
            with conn:
                conn.execute("INSERT INTO data (time, N2O_ppm, CO2_ppm, CH4_ppm, NH3_ppb) VALUES (?, ?, ?, ?, ?)", data)
        except Error as e:
            self.logger.error(f"Failed to insert status change: {e}")

    def query_data(self, last_plotted_time: Optional[str] = None, lim: int = 1000) -> List[Tuple]:
        conn = self.create_connection()
        with conn:
            cur = conn.cursor()
            if last_plotted_time is None:
                cur.execute(f"SELECT * FROM data ORDER BY time DESC LIMIT {lim}")
            else:
                cur.execute(f"SELECT * FROM data WHERE time > {last_plotted_time} ORDER BY time ASC")
            return cur.fetchall()


def main():
    HOST = '10.0.20.3'
    PORT = 51020
    db = Database('my_database.sqlite')
    db.create_tables()

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
