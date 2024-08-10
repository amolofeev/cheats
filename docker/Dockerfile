FROM python:3.12
ARG UID=1000
ARG GID=1000
ENV UID=${UID}
ENV GID=${GID}
RUN groupadd --gid ${GID} www &&\
    useradd --uid ${UID} --gid www --shell /bin/bash --create-home -d /www www

COPY . /www
RUN pip install --upgrade pip &&\
    pip install -r /www/requirements.txt &&\
    pip cache purge
WORKDIR /www

USER www
ENV PYTHONPATH=/www
CMD ["python", "-V"]
