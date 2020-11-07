FROM python:slim
ENV DEBIAN_FRONTEND noninteractive

EXPOSE 8181

RUN apt update && \
    apt install -y opus-tools ffmpeg libmagic-dev curl tar npm && \
    rm -rf /var/lib/apt/lists/*

COPY . /botamusique

WORKDIR /botamusique

RUN rm -rf .git*

RUN python3 -m venv venv && \
    venv/bin/pip install wheel && \
    venv/bin/pip install -r requirements.txt

RUN (cd web/ && npm install && npm run build)
RUN chmod +x entrypoint.sh

ENTRYPOINT [ "/botamusique/entrypoint.sh" ]
CMD ["venv/bin/python", "mumbleBot.py"]
