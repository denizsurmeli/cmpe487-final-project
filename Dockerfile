FROM python:3.8-slim-buster

WORKDIR /files

RUN apt update && apt install --no-install-recommends -y iproute2 \
    && rm -rf /var/cache/apt/archives /var/lib/apt/lists/*

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]