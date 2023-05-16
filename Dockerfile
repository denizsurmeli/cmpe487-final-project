FROM ubuntu:latest
RUN apt-get update && apt-get install -qq -y python3
COPY ./netchat.py /home/.

WORKDIR /home/.