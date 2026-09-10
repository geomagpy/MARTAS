import os
import sys
from magpy.core.database import DataBank

host = os.getenv("DB_HOST", "mariadb")
port = int(os.getenv("DB_PORT", 3306))
dbname = os.getenv("DB_NAME", "martas_db")
user = os.getenv("DB_USER", "martas_user")
passwd = os.getenv("DB_PASS", "MartasPasswort123!")

# TODO: Lege die credentials an

try:
    db = DataBank(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        passwd=passwd,
        dbtype="mysql"
    )
    db.dbinit()
    print("MagPy Datenbank erfolgreich via dbinit() initialisiert!")
except Exception as e:
    print(f"Fehler bei db.dbinit(): {e}", file=sys.stderr)
    sys.exit(1)