![Python](https://img.shields.io/badge/Python-3.10-blue) ![aiogram](https://img.shields.io/badge/aiogram-2.20-blue)
![sqlalchemy](https://img.shields.io/badge/SQLalchemy-1.4.36-springgreen) 
![sqlalchemy](https://img.shields.io/badge/Django-4.2.2-green)

---

### Setting it up

#### System dependencies

- Python 3.10
- Git

#### Preparations

1. Clone this repo via:
    - HTTPS `git clone https://github.com/illustratumq/instapuller-bot`
    - SSH `git clone git@github.com:illustratumq/instapuller-bot.git`
2. Move to the directory `cd aiogram-v2-template`
3. Rename `env.example` to `.env` and replace variables to your own

#### Regular Deployment

1. Create a virtual environment: `python -m venv venv`
2. Activate a virtual environment: `source ./venv/bin/activate` or `. ./venv/bin/activate`
3. Install requirements: `pip install -r requirements.txt`
4. Run your bot: `python -O bot.py`

#### Docker Deployment

1. **Note:** You need to have Docker and Docker Compose installed:
    - Debian-based distro: `sudo apt-get update -y && sudo apt-get upgrade -y && sudo apt install docker docker-compose`
2. Run command: `sudo docker pull selenoid/chrome:latest && sudo docker-compose up --build`