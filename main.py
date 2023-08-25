import subprocess


def main():
    # Start the database process
    database_process = subprocess.Popen(["python3", "database.py"])

    # Start the app process
    app_process = subprocess.Popen(["python3", "app.py"])

    try:
        # Wait indefinitely until the user stops the program
        while True:
            pass
    except KeyboardInterrupt:
        print("Terminating processes...")
        database_process.terminate()
        app_process.terminate()


if __name__ == "__main__":
    main()