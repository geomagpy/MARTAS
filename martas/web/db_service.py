# db_service.py
from martas.core import methods as mm

def get_db(credentials="cobsdb"):
    return mm.connect_db(credentials)

def get_sensors_metadata(db):
    # Beispiel: DATAINFO oder Tabellenliste abfragen
    cursor = db.db.cursor()
    cursor.execute("SELECT DataID, SensorID, DataSamplingRate, DataMinTime, DataMaxTime FROM DATAINFO")
    rows = cursor.fetchall()
    cursor.close()
    return [
        {
            "data_id": r[0],
            "sensor_id": r[1],
            "sampling_rate": r[2],
            "min_time": str(r[3]),
            "max_time": str(r[4]),
        }
        for r in rows
    ]

def get_measurements(db, data_id: str, limit: int = 100):
    if not data_id.replace("_", "").isalnum():
        raise ValueError("Ungültige DataID")
    stream = db.get_lines(data_id, limit)
    # In JSON-kompatibles Format umwandeln (z. B. Zeitstempel + Werte)
    return {
        "data_id": data_id,
        "count": stream.length()[0],
        "time": [t.isoformat() for t in stream.ndarray[0]],
        "x": stream.ndarray[1].tolist(),
    }