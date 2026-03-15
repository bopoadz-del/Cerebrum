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

# Install micromamba and create environment with ifcopenshell
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj -C /usr/local/bin --strip-components=1 bin/micromamba && \
    micromamba create -p /opt/conda python=3.11 ifcopenshell pillow -c conda-forge -y && \
    rm -rf /opt/conda/pkgs/cache

# Add conda to PATH
ENV PATH=/opt/conda/bin:$PATH

# Copy requirements and install via pip (conda env is in PATH)
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
