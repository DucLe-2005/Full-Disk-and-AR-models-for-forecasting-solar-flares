FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MPLBACKEND=Agg

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libglib2.0-0 \
    libgl1 \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/api.txt requirements/api.txt
COPY requirements/pipeline.txt requirements/pipeline.txt
COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/api.txt -r requirements/pipeline.txt

COPY app ./app
COPY prediction ./prediction

CMD ["python", "-m", "prediction.worker.run_worker"]
