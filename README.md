# LicenseHub Enterprise v1.0-dev0

Nyílt forráskódú, Docker-first licenckezelő platform Django, PostgreSQL 17, Redis, Celery és Nginx használatával.

## Gyors telepítés (Ubuntu Server 24.04)

```bash
git clone https://github.com/ceszes-hub/licensehub.git
cd licensehub
sudo bash install.sh
```

A telepítő erős titkokat és SAN mezős, RSA-3072 önaláírt TLS-tanúsítványt generál, majd kiírja a `/setup/` URL-t. Éles használathoz a tanúsítványt hiteles CA által kiadottra kell cserélni.

Teszt: `docker compose run --rm web pytest`.

- [Telepítési útmutató](docs/INSTALLATION.md)
- [Teljes backup és visszaállítás](docs/BACKUP_RESTORE.md)