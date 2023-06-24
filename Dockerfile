FROM python:3-slim-bullseye AS python-builder
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /botamusique

RUN apt-get update \
    && apt-get install --no-install-recommends -y gcc g++ ffmpeg libjpeg-dev libmagic-dev opus-tools zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
COPY . /botamusique

RUN python3 -m venv venv \
    && venv/bin/pip install wheel \
    && venv/bin/pip install -r requirements.txt


FROM python:3-slim-bullseye
ENV DEBIAN_FRONTEND noninteractive
EXPOSE 8181
RUN apt update && \
    apt install --no-install-recommends -y opus-tools ffmpeg libmagic-dev curl tar && \
    rm -rf /var/lib/apt/lists/*
COPY --from=python-builder /botamusique /botamusique
WORKDIR /botamusique
RUN chmod +x entrypoint.sh

ENTRYPOINT [ "/botamusique/entrypoint.sh" ]
CMD ["venv/bin/python", "mumbleBot.py"]
