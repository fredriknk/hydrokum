# HYDROKUMMER

## Description

This project aims to provide a web-based interface to monitor and control PLCs 
(Programmable Logic Controllers) using Snap7 and Dash. It also incorporates 
data storage solutions using SQLite3 and provides real-time graphical representation 
of the data using Plotly.

## Features

- Real-time monitoring of PLCs
- Web-based control panel built using Dash
- Data storage with SQLite3
- Real-time graphical representations using Plotly
- Logging functionality for debug and traceability

## Prerequisites

- Python 3.x
- Pip
- Virtualenv (recommended)

## Installation

### Clone the Repository

```bash
git clone https://github.com/fredriknk/hydrokum.git
cd hydrokum
```

### Create and Activate Virtual Environment (recommended)

```bash
python3 -m venv hydrohus
source hydrohus/bin/activate  # 
```
windows
```bash
python3 -m venv hydrohus
source hydrohus\Scripts\activate`
```

### Install Requirements

```bash
pip install -r requirements.txt
```

## Usage

### Running the Web App

```bash
# Make sure you're in the project directory and virtual environment is activated
python main.py
```

Open your web browser and go to `http://127.0.0.1:8050/`

### Environment Variables

To set environment variables, create a `.env` file in the project root and specify the variables:

```env
USER_NAME=admin
PASSWORD=###
BASE_URL=http://IP/cgi-bin/api.cgi?cmd=Snap&channel=0&rs=wuuPhkmUCeI9WG7C
```

## Contributing

Feel free to open issues and pull requests!

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
