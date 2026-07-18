# LicenseHub full backup and restore

A full backup bundle contains the PostgreSQL database and roles, uploaded media, `.env`, Compose configuration, Nginx configuration, TLS certificates, and the rclone cloud configuration. Static files and Redis cache are regenerated and are intentionally not archived.

## Local storage location

Set the host directory in `.env` before starting Compose:

```env
BACKUP_HOST_PATH=/srv/licensehub-backups
```

The retention period, schedule, local subdirectory, and destination are configurable under **Settings → Backup**.

## Cloud storage

The backup container uses rclone. Create its configuration interactively:

```sh
mkdir -p docker/backup/rclone
docker compose run --rm \
  -v "$(pwd)/docker/backup/rclone:/root/.config/rclone" \
  --entrypoint rclone backup config
```

Create a remote named `amazon`, `azure`, or `sharepoint`, then enter a destination such as `amazon:licensehub`, `azure:licensehub`, or `sharepoint:LicenseHub` in the Backup settings page. Amazon S3, Azure Blob Storage and SharePoint/OneDrive use the corresponding rclone backend and authentication flow.

## Manual backup

Use the web button or run:

```sh
bash scripts/backup.sh
```

## Download a cloud backup

On a replacement server, configure the same rclone remote and download both the archive and checksum into the local backup storage:

```sh
bash scripts/cloud-download.sh amazon:licensehub licensehub_full_YYYYMMDDTHHMMSSZ.tar.gz
```

Use `azure:licensehub` or `sharepoint:LicenseHub` for the other providers.
## Full restore

On a fresh LicenseHub checkout, make the backup volume/directory available and run:

```sh
bash scripts/restore.sh licensehub_full_YYYYMMDDTHHMMSSZ.tar.gz
```

The script verifies both checksum layers, stops application services, replaces the database and uploaded media, restores local configuration, rebuilds containers, runs migrations and static collection, then starts the complete stack. It requires typing `RESTORE` before destructive operations.
## SMB network share

Select **SMB network share** under Settings → Backup and enter the server/IP, port 445, share, optional subdirectory/domain, username and password. The password is encrypted in PostgreSQL. The backup container creates a temporary rclone configuration only while the backup runs. Use a dedicated SMB 3 account restricted to the LicenseHub backup directory.

## Network configuration

Configure DHCP or a static address under Settings → Network. Apply the generated Netplan configuration from the Ubuntu console:

```sh
sudo bash scripts/apply-network-config.sh
```

`netplan try` rolls the change back after 120 seconds unless it is confirmed. Existing files are copied to `/var/backups/licensehub-netplan/` before applying the change.