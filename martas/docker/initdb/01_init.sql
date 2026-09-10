-- Leere Datenbank anlegen
CREATE DATABASE IF NOT EXISTS martas_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Lese-/Schreibnutzer für die Anwendung anlegen
CREATE USER IF NOT EXISTS 'martas_user'@'%' IDENTIFIED BY 'MartasPasswort123!';
GRANT ALL PRIVILEGES ON martas_db.* TO 'martas_user'@'%';

-- Admin User für Optimize
CREATE USER IF NOT EXISTS 'admin'@'%' IDENTIFIED BY 'ReadPasswort123!';
GRANT SELECT ON *.* TO 'admin'@'%';

FLUSH PRIVILEGES;