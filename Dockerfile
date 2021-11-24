FROM alpine:3.14.3

RUN apk --no-cache add \
    bash \
    git \
    docker \
    python3 \
    py3-pip \
    && pip3 install awscli

# Copies your code file from your action repository to the filesystem path `/` of the container
COPY *.sh /usr/local/bin

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["entrypoint.sh"]
