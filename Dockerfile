FROM python:3.10-buster

EXPOSE 4444-4448
EXPOSE 8000

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBEFFERED=1

WORKDIR /src

COPY . /src

RUN python -m pip install --upgrade pip && python -m pip install --requirement requirements.txt
