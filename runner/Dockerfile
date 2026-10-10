FROM gitea/act_runner:0.2.11
USER root
RUN apk add --no-cache bash curl git python3 py3-pip docker-cli
RUN curl -sSLo /usr/local/bin/kubectl \
      "https://dl.k8s.io/release/v1.31.5/bin/linux/$(uname -m | sed 's/x86_64/amd64/; s/aarch64/arm64/')/kubectl" \
    && chmod +x /usr/local/bin/kubectl
ENV PIP_BREAK_SYSTEM_PACKAGES=1
