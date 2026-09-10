FROM python:3.10-slim

# System-Abhängigkeiten installieren
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    git \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# MagPy und MARTAS installieren
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir magpy martas mysqlconnector-python mariadb dash gunicorn

# Skripte kopieren
COPY init_magpy.py /app/init_magpy.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8050

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "-m", "martas.gui.dash_app"]