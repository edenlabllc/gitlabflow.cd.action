FROM alpine:3.15.2

RUN apk --no-cache add \
    bash \
    curl \
    git \
    docker \
    python3 \
    py3-pip \
    bind-tools \
    && pip3 install awscli

# Copies your code file from your action repository to the filesystem path `/` of the container
COPY *.sh /usr/local/bin

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["entrypoint.sh"]
