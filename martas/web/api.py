# api.py
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import db_service

app = FastAPI(
    title="MARTAS Data API",
    description="REST-Schnittstelle für Messdaten und Metadaten auf dem DB-Kollektor",
    version="1.0.0",
)

# Zugriff aus dem lokalen Netz / anderen Web-Apps erlauben
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Im Produktivnetz ggf. auf Subnetz/IPs einschränken
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/api/v1/meta")
def read_metadata():
    db = db_service.get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Datenbank nicht erreichbar")
    return {"sensors": db_service.get_sensors_metadata(db)}

@app.get("/api/v1/data/{data_id}")
def read_measurements(data_id: str, limit: int = Query(100, ge=1, le=50000)):
    db = db_service.get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Datenbank nicht erreichbar")
    try:
        return db_service.get_measurements(db, data_id, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "service": "fastapi"}


@app.get("/api/v1/database")
def database_check():
    try:
        return db_service.get_database_info()
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/status/{status_id}")
def get_status_by_id(status_id: str):
    """Liest den Statuseintrag anhand der 'status_id' aus der Tabelle COBSSTATUS aus."""
    try:
        result = db_service.get_status_by_id(status_id)
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result is None:
        raise HTTPException(status_code=404, detail=f"status_id '{status_id}' nicht gefunden.")

    return result

@app.get("/api/v1/location")
def get_locations(
    max_age_minutes: int = Query(
        60,
        ge=1,
        le=43200,
        description="Maximales Alter von DataMaxTime in Minuten, damit ein Sensor als active=true gilt",
    ),
    unique_sensors: bool = Query(
        False,
        description="Wenn true, wird pro SensorID nur ein Feature zurückgegeben",
    ),
):
    """
    Liefert alle Sensor-Standorte aus DATAINFO als GeoJSON FeatureCollection (WGS84 / EPSG:4326)
    inklusive Aktivitäts-Flag für die Kartendarstellung.
    """
    try:
        return db_service.get_locations_geojson(
            max_age_minutes=max_age_minutes,
            only_latest_per_sensor=unique_sensors,
        )
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/timeseries/{dataid}")
def get_timeseries_by_id(
    dataid: str,
    background_tasks: BackgroundTasks,
    starttime: str | None = Query(
        None,
        description="Startzeitpunkt (ISO oder YYYY-MM-DD HH:MM:SS). Default: 24h vor endtime bzw. jetzt.",
    ),
    endtime: str | None = Query(
        None,
        description="Endzeitpunkt (ISO oder YYYY-MM-DD HH:MM:SS). Default: aktueller UTC-Zeitpunkt.",
    ),
    format: str = Query(
        "covjson",
        description="Ausgabeformat: 'covjson' (Standard), 'json' für Charts, oder 'csv', 'iaga', 'pycdf', etc.",
    ),
    keys: str | None = Query(
        None,
        description="Kommagetrennte Spalten/Keys (z.B. 'x,y,z,f')",
    ),
    coordinates: str | None = Query(
        None,
        description="Koordinatensystem (xyz, hez, idf)",
    ),
):
    """
    Liest eine Zeitserie aus der MagPy/MARTAS-Datenbank aus und gibt sie standardmäßig als CovJSON zurück.
    Ohne 'starttime' wird automatisch ein 24-Stunden-Fenster verwendet.
    """
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    # 1. Endzeitpunkt parsen oder auf 'jetzt (UTC)' setzen
    if endtime:
        try:
            end_dt = date_parser.parse(endtime)
            if end_dt.tzinfo is not None:
                end_dt = end_dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Ungültiges Datumsformat bei 'endtime'.",
            )
    else:
        end_dt = now_utc

    # 2. Startzeitpunkt parsen oder auf 24 Stunden vor 'end_dt' setzen
    if starttime:
        try:
            start_dt = date_parser.parse(starttime)
            if start_dt.tzinfo is not None:
                start_dt = start_dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Ungültiges Datumsformat bei 'starttime'.",
            )
    else:
        start_dt = end_dt - timedelta(hours=24)

    # 3. Zeitraum validieren (max. 31 Tage)
    if end_dt < start_dt:
        raise HTTPException(
            status_code=400,
            detail="'endtime' darf nicht vor 'starttime' liegen.",
        )

    if (end_dt - start_dt) > timedelta(days=31):
        raise HTTPException(
            status_code=400,
            detail="Der angeforderte Zeitraum darf maximal 31 Tage betragen.",
        )

    # Formatierte UTC-Strings für MagPy / Dateinamen erzeugen
    resolved_start = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    resolved_end = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    try:
        result = db_service.get_timeseries_export(
            data_id=dataid,
            starttime=resolved_start,
            endtime=resolved_end,
            req_format=format,
            keys=keys,
            coordinates=coordinates,
        )
    except db_service.TimeseriesNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei der Datenverarbeitung: {str(e)}")

    # Antwort je nach Ergebnis-Typ ausliefern
    if result["kind"] == "json":
        return result["payload"]

    if result["kind"] == "text":
        return Response(
            content=result["content"],
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f"inline; filename={result['filename']}"
            },
        )

    if result["kind"] == "file":
        background_tasks.add_task(
            db_service.cleanup_temp_files,
            result["path"],
            result["temp_dir"],
        )
        return FileResponse(
            path=result["path"],
            filename=result["filename"],
            media_type=result["media_type"],
        )
