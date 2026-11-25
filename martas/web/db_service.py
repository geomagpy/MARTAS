# db_service.py
import re
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pyproj import Transformer
from martas.core import methods as mm
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
import numpy as np
from magpy.stream import SUPPORTED_FORMATS


@contextmanager
def get_db(credentials: str = "cobsdb"):
    """Context-Manager für die MagPy-DB-Verbindung (schließt automatisch nach Nutzung)."""
    conn = mm.connect_db(credentials)
    if not conn:
        raise ConnectionError("Datenbankverbindung konnte nicht hergestellt werden.")
    try:
        yield conn
    finally:
        if hasattr(conn, "db") and getattr(conn.db, "open", False):
            conn.db.close()


def get_database_info() -> dict:
    """Ruft die MagPy-Datenbankinformationen ab."""
    with get_db() as conn:
        report = conn.info(destination="stdout")
        return {"database_information": report}


def get_status_by_id(status_id: str) -> dict | None:
    """Liest den vollständigen Statuseintrag anhand der status_notation aus COBSSTATUS."""
    sql = """
        SELECT 
            status_notation,
            status_value,
            value_unit,
            active,
            validity_start,
            validity_end,
            value_min,
            value_max
        FROM COBSSTATUS
        WHERE status_notation = %s
        LIMIT 1
    """
    with get_db() as conn:
        cursor = conn.db.cursor()
        try:
            cursor.execute(sql, (status_id,))
            row = cursor.fetchone()
        finally:
            cursor.close()

    if not row:
        return None

    return {
        "status_notation": row[0],
        "status_value": row[1],
        "status_unit": row[2] or "",
        "status_active": row[3] if row[3] is not None else 0,
        "validity_start": row[4].isoformat() if hasattr(row[4], "isoformat") else row[4],
        "validity_end": row[5].isoformat() if hasattr(row[5], "isoformat") else row[5],
        "value_min": row[6],
        "value_max": row[7],
    }

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

@lru_cache(maxsize=32)
def _get_transformer(epsg_code: int) -> Transformer:
    """Cached pyproj Transformer von Quell-EPSG nach WGS84 (EPSG:4326)."""
    return Transformer.from_crs(f"EPSG:{epsg_code}", "EPSG:4326", always_xy=True)


def _convert_to_wgs84(lat_val: float, lon_val: float, loc_ref: str | None) -> tuple[float, float]:
    """
    Konvertiert Koordinaten nach WGS84 (lon, lat).
    Erkennt EPSG-Codes aus DataLocationReference (z.B. 'GK M34, EPSG: 31253').
    """
    epsg_code = 4326
    if loc_ref:
        match = re.search(r"EPSG:\s*(\d+)", loc_ref, re.IGNORECASE)
        if match:
            epsg_code = int(match.group(1))

    if epsg_code == 4326:
        return float(lon_val), float(lat_val)

    transformer = _get_transformer(epsg_code)
    # always_xy=True erwartet (Easting/Longitude, Northing/Latitude) -> liefert (lon, lat)
    lon_wgs, lat_wgs = transformer.transform(float(lon_val), float(lat_val))
    return round(lon_wgs, 7), round(lat_wgs, 7)


def get_locations_geojson(
    max_age_minutes: int = 60,
    only_latest_per_sensor: bool = False,
) -> dict:
    """
    Liest Koordinaten und Metadaten aus DATAINFO und erzeugt eine GeoJSON FeatureCollection.
    """
    sql = """
        SELECT
            DataID,
            SensorID,
            StationID,
            DataMinTime,
            DataMaxTime,
            DataSamplingRate,
            DataAcquisitionLatitude,
            DataAcquisitionLongitude,
            DataLocationReference,
            DataElevation,
            DataElevationRef,
            DataComments,
            ColumnContents
        FROM DATAINFO
        WHERE DataAcquisitionLatitude IS NOT NULL
          AND DataAcquisitionLongitude IS NOT NULL
        ORDER BY DataID ASC
    """
    with get_db() as conn:
        cursor = conn.db.cursor()
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
        finally:
            cursor.close()

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    features = []
    seen_sensors = set()

    for row in rows:
        (
            data_id,
            sensor_id,
            station_id,
            min_time,
            max_time,
            sampling_rate,
            lat_raw,
            lon_raw,
            loc_ref,
            elevation,
            elev_ref,
            comments,
            col_contents,
        ) = row

        # Optional: nur einen Marker pro SensorID (falls mehrere Revisions-DataIDs existieren)
        if only_latest_per_sensor and sensor_id in seen_sensors:
            continue

        try:
            lon_wgs, lat_wgs = _convert_to_wgs84(lat_raw, lon_raw, loc_ref)
        except Exception:
            # Ungültige Koordinaten oder unbekannter EPSG-Code überspringen
            continue

        # Aktiv-Status bestimmen
        is_active = False
        max_dt = None
        if max_time:
            max_dt = (
                datetime.fromisoformat(str(max_time))
                if isinstance(max_time, str)
                else max_time
            )
            # Toleranz: mind. max_age_minutes, oder 3x Samplingrate bei langsamen Sensoren
            tolerance_sec = max(max_age_minutes * 60, (float(sampling_rate or 0) * 3))
            if (now_utc - max_dt) <= timedelta(seconds=tolerance_sec):
                is_active = True

        if only_latest_per_sensor:
            seen_sensors.add(sensor_id)

        # GeoJSON Coordinates: [lon, lat] oder [lon, lat, elevation]
        coords = [lon_wgs, lat_wgs]
        if elevation is not None:
            coords.append(float(elevation))

        features.append(
            {
                "type": "Feature",
                "id": data_id,
                "geometry": {
                    "type": "Point",
                    "coordinates": coords,
                },
                "properties": {
                    "data_id": data_id,
                    "sensor_id": sensor_id,
                    "station_id": station_id,
                    "active": is_active,
                    "marker_color": "#2ecc71" if is_active else "#95a5a6",
                    "data_min_time": min_time.isoformat() if hasattr(min_time, "isoformat") else str(min_time) if min_time else None,
                    "data_max_time": max_dt.isoformat() if max_dt else None,
                    "sampling_rate": float(sampling_rate) if sampling_rate is not None else None,
                    "elevation": float(elevation) if elevation is not None else None,
                    "elevation_ref": elev_ref,
                    "source_crs": loc_ref,
                    "contents": col_contents.strip(",") if col_contents else None,
                    "comments": comments,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "generated_at": now_utc.isoformat() + "Z",
        "features": features,
    }


class TimeseriesNotFoundError(Exception):
    """Wird geworfen, wenn keine Zeitreihendaten gefunden wurden."""


def cleanup_temp_files(file_path: str | None, temp_dir: str):
    """Löscht temporäre Export-Dateien und das zugehörige Temp-Verzeichnis."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass


def get_timeseries_export(
    data_id: str,
    starttime: str | None = None,
    endtime: str | None = None,
    req_format: str = "covjson",
    keys: str | None = None,
    coordinates: str | None = None,
) -> dict:
    """
    Liest eine Zeitserie über MagPy aus und bereitet sie je nach Zielformat auf.
    Gibt ein strukturiertes Ergebnis-Dict für den FastAPI-Endpoint zurück.
    """
    if "GICAUT" in data_id:
        raise TimeseriesNotFoundError(f"Keine Daten für dataid '{data_id}' im gewählten Zeitraum gefunden.")

    with get_db() as conn:
        data = conn.read(data_id, starttime=starttime, endtime=endtime)

    if data is None or len(data) == 0:
        raise TimeseriesNotFoundError(f"Keine Daten für dataid '{data_id}' im gewählten Zeitraum gefunden.")

    # Optional: Koordinatentransformation (z.B. xyz -> hez / idf), falls gewünscht
    if coordinates:
        coord_target = coordinates.lower().strip()
        if coord_target in ("hez", "idf", "xyz") and hasattr(data, "xyz2hdz"):
            # Hier bei Bedarf MagPy-Konvertierung aktivieren (z.B. data = data.xyz2hdz())
            pass

    # Verfügbare Variablen bestimmen und optional nach 'keys' filtern
    available_keys = data.variables()
    if keys:
        requested_keys = [k.strip() for k in keys.split(",") if k.strip()]
        datakeys = [k for k in requested_keys if k in available_keys]
        if not datakeys:
            raise ValueError(f"Keine der angeforderten Keys {requested_keys} in '{data_id}' vorhanden.")
    else:
        datakeys = available_keys

    fmt_upper = req_format.upper().strip()

    # Format-Validierung: COVJSON und JSON direkt erlauben, sonst SUPPORTED_FORMATS prüfen
    if fmt_upper in ("COVJSON", "JSON"):
        format_type = fmt_upper
    else:
        cont = SUPPORTED_FORMATS.get(fmt_upper, [])
        format_type = fmt_upper if (len(cont) > 0 and "w" in cont[0]) else "COVJSON"

    # --- FALL 1: COVJSON (Default) ---
    if format_type == "COVJSON":
        string_io_file = data.write("StringIO", coverage="all", format_type="COVJSON")
        if not string_io_file:
            raise RuntimeError("Fehler beim Erstellen der CovJSON-Daten.")

        raw_content = string_io_file.getvalue()
        string_io_file.close()

        try:
            payload = json.loads(raw_content)
        except json.JSONDecodeError:
            # NaN / Infinity Werte gemäß RFC 8259 durch null ersetzen
            clean_content = re.sub(r"\b-?(?:NaN|nan|Infinity)\b", "null", raw_content)
            payload = json.loads(clean_content)

        return {"kind": "json", "payload": payload}

    # --- FALL 2: Standard JSON für Diagramme ---
    if format_type == "JSON":
        time_list = [
            t.isoformat() if hasattr(t, "isoformat") else str(t)
            for t in data.ndarray[0]
        ]
        data_dict = {"time": time_list}
        for key in datakeys:
            col_data = data._get_column(key)
            data_dict[key] = [
                None if (isinstance(val, (float, np.floating)) and np.isnan(val)) else float(val)
                for val in col_data
            ]

        return {
            "kind": "json",
            "payload": {
                "status": "success",
                "dataid": data_id,
                "header": dict(data.header),
                "data": data_dict,
            },
        }

    # --- FALL 3: String In-Memory Formate (IAGA, PYSTR, CSV) ---
    if format_type in ("IAGA", "PYSTR", "CSV"):
        string_io_file = data.write("StringIO", coverage="all", format_type=format_type)
        if not string_io_file:
            raise RuntimeError(f"Fehler beim Erstellen der {format_type}-Textdaten.")

        content = string_io_file.getvalue()
        string_io_file.close()
        ext = "min" if format_type == "IAGA" else format_type.lower()

        return {
            "kind": "text",
            "content": content,
            "filename": f"{data_id}_{starttime or 'all'}.{ext}",
        }

    # --- FALL 4: Binär- & Datei-Downloads (PYCDF, IMAGCDF, etc.) ---
    clean_dataid = data_id.replace(" ", "_")
    filename_begins = f"{clean_dataid}_{starttime or 'all'}"
    filename_ends = f".{format_type.lower()}"
    temp_dir = tempfile.mkdtemp()

    try:
        fn = data.write(
            temp_dir,
            filenamebegins=filename_begins,
            filenameends=filename_ends,
            coverage="all",
            format_type=format_type,
        )

        if fn and isinstance(fn, str) and os.path.isabs(fn) and os.path.exists(fn):
            fullpath = fn
        else:
            matches = sorted(Path(temp_dir).glob(f"{filename_begins}*"))
            if not matches:
                raise RuntimeError("Erstellung der Export-Datei fehlgeschlagen.")
            fullpath = str(matches[0].resolve())

        return {
            "kind": "file",
            "path": fullpath,
            "temp_dir": temp_dir,
            "filename": os.path.basename(fullpath),
            "media_type": "application/octet-stream",
        }
    except Exception:
        cleanup_temp_files(None, temp_dir)
        raise
