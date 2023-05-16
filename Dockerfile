FROM ubuntu:latest
RUN apt-get update && apt-get install -qq -y python3
COPY ./chat.py /home/.

WORKDIR /home/.