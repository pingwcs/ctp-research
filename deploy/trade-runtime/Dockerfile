FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        ca-certificates \
        libstdc++6 \
        pkg-config \
        python3 \
        python3-dev \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages --upgrade \
        pip==25.1.1 \
        meson==1.8.3 \
        meson-python==0.18.0 \
        pybind11==2.13.6

COPY deploy/trade-runtime/requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --break-system-packages --no-binary=vnpy_ctp \
        -r /tmp/requirements.txt

COPY trade_runtime /opt/ctp_research/trade_runtime
COPY scripts/verify_ctp_runtime.py /opt/ctp_research/scripts/verify_ctp_runtime.py

RUN useradd --create-home --uid 10001 trader \
    && chown -R trader:trader /opt/ctp_research

USER trader
WORKDIR /opt/ctp_research

CMD ["python3", "scripts/verify_ctp_runtime.py"]
