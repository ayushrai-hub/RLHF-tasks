FROM public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c

RUN apt-get update \
    && apt-get install -y --no-install-recommends tmux asciinema meson ninja-build pkg-config binutils file python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --break-system-packages --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

WORKDIR /app

COPY Makefile /app/environment/Makefile
COPY meson.build /app/environment/meson.build
COPY meson_options.txt /app/environment/meson_options.txt
COPY include /app/environment/include
COPY src /app/environment/src
COPY tools /app/environment/tools
COPY client /app/environment/client
COPY checks /app/environment/checks
COPY scripts /app/environment/scripts
COPY ambient /app/environment/ambient
COPY data /app/environment/data
COPY docs /app/environment/docs
