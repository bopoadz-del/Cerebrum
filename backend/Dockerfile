FROM python:3.11-slim

ENV PYTHONDONTWRITECODE=1
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
    wget \
    bzip2 \
    ca-certificates \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Miniconda + accept ToS + Python 3.11 in one layer
ENV CONDA_DIR=/opt/conda
ENV PATH=$CONDA_DIR/bin:$PATH
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p $CONDA_DIR && \
    rm /tmp/miniconda.sh && \
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && \
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r && \
    conda install python=3.11 -y && \
    conda clean -afy

# Install ifcopenshell and Pillow via conda-forge (with Python 3.11 pinned)
RUN conda install -c conda-forge ifcopenshell pillow pip -y && \
    conda clean -afy

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
