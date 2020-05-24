FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y deluged \
                       transmission-daemon \
                       qbittorrent-nox \
                       rtorrent \
                       python3 \
                       python3-pip \
                       && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install -U setuptools pip wheel
ADD test-requirements.txt /
RUN pip3 install -r /test-requirements.txt