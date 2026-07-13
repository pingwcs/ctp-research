FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace

COPY data_pipeline/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY data_pipeline ./data_pipeline
COPY market_data ./market_data
COPY platform_config.py ./

ENTRYPOINT ["python", "data_pipeline/run.py"]
CMD ["--input-dir", "/data/input", "--output-dir", "/data/output", "--market-root", "/data/market", "--no-influx"]
