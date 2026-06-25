# .NET/C# has no canonical base image, so we rebase on the canonical Debian
# slim image and install the pinned .NET SDK ourselves via dotnet-install.sh.
# The agent compiles the project, so the SDK must live in the runtime image.
FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

WORKDIR /app

ENV DOTNET_NOLOGO=1
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1
ENV DOTNET_EnableDiagnostics=0
ENV DOTNET_GENERATE_ASPNET_CERTIFICATE=false
ENV DOTNET_USE_POLLING_FILE_WATCHER=true
ENV NUGET_XMLDOC_MODE=skip
ENV DEBIAN_FRONTEND=noninteractive
ENV DOTNET_ROOT=/usr/share/dotnet
ENV PATH=/usr/share/dotnet:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-pip \
        tmux \
        asciinema \
        ca-certificates \
        curl \
        libicu72 \
        libssl3 \
        zlib1g \
        libstdc++6 \
        libgcc-s1 \
        bash \
        coreutils \
    && rm -rf /var/lib/apt/lists/*

# Pinned .NET SDK install. The SDK version is fixed to match Seismic/global.json.
RUN curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh \
    && chmod +x /tmp/dotnet-install.sh \
    && /tmp/dotnet-install.sh --version 8.0.414 --install-dir /usr/share/dotnet \
    && rm /tmp/dotnet-install.sh \
    && ln -s /usr/share/dotnet/dotnet /usr/local/bin/dotnet

RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5 \
        numpy==2.2.6 \
        scipy==1.14.1

RUN mkdir -p /app/Seismic /app/Seismic/Properties /app/input /app/output /app/fixtures /app/docs /app/scripts

COPY Seismic/Seismic.csproj /app/Seismic/Seismic.csproj
COPY Seismic/Directory.Build.props /app/Seismic/Directory.Build.props
COPY Seismic/Program.cs /app/Seismic/Program.cs
COPY Seismic/global.json /app/Seismic/global.json
COPY Seismic/nuget.config /app/Seismic/nuget.config
COPY Seismic/.editorconfig /app/Seismic/.editorconfig
COPY Seismic/.gitignore /app/Seismic/.gitignore
COPY Seismic/Properties/launchSettings.json /app/Seismic/Properties/launchSettings.json
COPY fixtures/layered_simple.json /app/fixtures/layered_simple.json
COPY fixtures/layered_with_salt.json /app/fixtures/layered_with_salt.json
COPY fixtures/layered_with_fault.json /app/fixtures/layered_with_fault.json
COPY fixtures/layered_fault_salt.json /app/fixtures/layered_fault_salt.json
COPY fixtures/layered_multi_fault.json /app/fixtures/layered_multi_fault.json
COPY fixtures/model_homo.json /app/fixtures/model_homo.json
COPY fixtures/model_homo_elastic.json /app/fixtures/model_homo_elastic.json
COPY fixtures/model_two_layer.json /app/fixtures/model_two_layer.json
COPY fixtures/source_ricker.json /app/fixtures/source_ricker.json
COPY fixtures/source_explosive.json /app/fixtures/source_explosive.json
COPY fixtures/source_vibroseis.json /app/fixtures/source_vibroseis.json
COPY fixtures/source_ricker25.json /app/fixtures/source_ricker25.json
COPY fixtures/source_ricker20.json /app/fixtures/source_ricker20.json
COPY fixtures/sim_homo_off.json /app/fixtures/sim_homo_off.json
COPY fixtures/sim_homo_on.json /app/fixtures/sim_homo_on.json
COPY fixtures/sim_homo_attn.json /app/fixtures/sim_homo_attn.json
COPY fixtures/sim_homo_vz.json /app/fixtures/sim_homo_vz.json
COPY fixtures/sim_homo_swave.json /app/fixtures/sim_homo_swave.json
COPY fixtures/sim_two_layer.json /app/fixtures/sim_two_layer.json
COPY fixtures/rtm_two_layer.json /app/fixtures/rtm_two_layer.json
COPY fixtures/avo_two_layer.json /app/fixtures/avo_two_layer.json
COPY fixtures/qc_two_layer.json /app/fixtures/qc_two_layer.json
COPY fixtures/sweep_two_layer.json /app/fixtures/sweep_two_layer.json
COPY docs/architecture.md /app/docs/architecture.md
COPY docs/model_schema.md /app/docs/model_schema.md
COPY docs/source_schema.md /app/docs/source_schema.md
COPY docs/simulate_schema.md /app/docs/simulate_schema.md
COPY docs/imaging_schema.md /app/docs/imaging_schema.md
COPY docs/npy_format.md /app/docs/npy_format.md
COPY docs/build.md /app/docs/build.md
COPY scripts/build.sh /app/scripts/build.sh
COPY scripts/clean.sh /app/scripts/clean.sh
COPY scripts/run.sh /app/scripts/run.sh

RUN chmod +x /app/scripts/*.sh && cd /app/Seismic && dotnet restore --verbosity quiet

RUN find /tmp -mindepth 1 -delete 2>/dev/null || true
