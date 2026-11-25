# api.py
from fastapi import FastAPI, HTTPException, Query
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