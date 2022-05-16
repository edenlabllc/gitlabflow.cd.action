FROM alpine:3.15

RUN apk --no-cache add \
    bash \
    curl \
    git \
    docker \
    python3 \
    py3-pip \
    bind-tools \
    && pip3 install awscli

# install manually to pass image scanning, see https://github.com/stedolan/jq/issues/1406#issuecomment-672270758
ARG JQ_VERSION=1.6
RUN cd /tmp \
    && wget https://github.com/stedolan/jq/releases/download/jq-${JQ_VERSION}/jq-linux64 -O jq-linux64 \
    && chmod a+x jq-linux64 \
    && mv jq-linux64 /usr/local/bin/jq \
    && jq --version

# Copies your code file from your action repository to the filesystem path `/` of the container
COPY *.sh /usr/local/bin

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["entrypoint.sh"]
