FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace

COPY appapi/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY appapi ./appapi
COPY market_data ./market_data
COPY quant_runtime ./quant_runtime
COPY global_config.py platform_config.py ./

RUN adduser --disabled-password --gecos "" --uid 10001 appapi \
    && chown -R appapi:appapi /workspace

USER appapi

CMD ["python", "-m", "appapi.main"]
