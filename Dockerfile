ARG ARCH=
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

FROM ${ARCH}node:14-bullseye-slim AS node-builder
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /botamusique/web
COPY --from=python-builder /botamusique /botamusique
RUN npm install
RUN npm run build

FROM ${ARCH}python:3-slim-bullseye AS template-builder
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /botamusique
COPY --from=node-builder /botamusique /botamusique
RUN venv/bin/python scripts/translate_templates.py --lang-dir /botamusique/lang --template-dir /botamusique/web/templates


FROM python:3-slim-bullseye
ENV DEBIAN_FRONTEND noninteractive
EXPOSE 8181
RUN apt update && \
    apt install --no-install-recommends -y opus-tools ffmpeg libmagic-dev curl tar && \
    rm -rf /var/lib/apt/lists/*
COPY --from=template-builder /botamusique /botamusique
WORKDIR /botamusique
RUN chmod +x entrypoint.sh

ENTRYPOINT [ "/botamusique/entrypoint.sh" ]
CMD ["venv/bin/python", "mumbleBot.py"]
