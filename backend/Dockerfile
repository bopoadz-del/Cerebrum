FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libpq5 \
    postgresql-client \
    curl \
    bzip2 \
    ca-certificates \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Install micromamba (lightweight conda alternative, no ToS)
ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV PATH=/opt/conda/bin:$PATH
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj -C /tmp bin/micromamba && \
    mv /tmp/bin/micromamba /usr/local/bin/micromamba && \
    micromamba shell init -s bash -p /opt/conda && \
    micromamba install python=3.11 ifcopenshell pillow -c conda-forge -y && \
    rm -rf /opt/conda/pkgs/cache

# Copy requirements and install via pip
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Verify ifcopenshell
RUN python -c "import ifcopenshell; print(f'ifcopenshell: {ifcopenshell.version}')"

# Cache bust
COPY .docker_nocache /tmp/.docker_nocache
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
