# LicenseHub Enterprise v1.0-dev0

Ny?lt forr?sk?d?, Docker-first licenckezel?si alapplatform Django, PostgreSQL 17, Redis, Celery ?s Nginx haszn?lat?val.

## Gyors telep?t?s (Ubuntu Server 24.04)

```bash
git clone https://github.com/ceszes-hub/licensehub.git
cd licensehub
sudo ./install.sh
```

A telep?t? er?s titkokat ?s SAN mez?s, RSA-3072 ?nal??rt TLS-tan?s?tv?nyt gener?l, majd ki?rja a `/setup/` URL-t. ?les haszn?lathoz cser?lje a tan?s?tv?nyt hiteles CA ?ltal kiadottra.

Teszt: `docker compose run --rm web pytest`. R?szletek: [docs/INSTALLATION.md](docs/INSTALLATION.md).
