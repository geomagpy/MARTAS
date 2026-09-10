#!/bin/bash
set -e

echo "1. Warte auf Datenbank-Verbindung ($DB_HOST:$DB_PORT)..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "Datenbank ist erreichbar!"

# 2. MagPy Datenbank-Initialisierung über db.dbinit()
echo "2. Führe MagPy dbinit() aus..."
python /app/init_magpy.py

# 3. martas_init mit automatischen Antworten ausführen (falls noch nicht geschehen)
if [ ! -d "/app/martas_config" ] || [ -z "$(ls -A /app/martas_config)" ]; then
  echo "3. Führe martas_init aus..."
  mkdir -p /app/martas_config /app/martas_data

  martas_init <<ANSWERS
/app/martas_config
/app/martas_data
y
ANSWERS
else
  echo "3. martas_config existiert bereits, überspringe martas_init."
fi

# 4. Haupt-Anwendung starten
echo "4. Starte MARTAS Server..."
exec "$@"