FROM python:3.9.13-slim

COPY . /yourls-action
WORKDIR /yourls-action
RUN \
    pip3 install -r requirements.txt \
    && pip3 install -e .

ENTRYPOINT [ "yourls-action", "run" ]
CMD [ "/namespaces" ]
