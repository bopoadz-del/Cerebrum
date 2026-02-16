"""
Database Backup Automation

Automates database backups using pg_dump and uploads to S3.
Supports full and incremental backups with retention policies.
"""

import asyncio
import gzip
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import boto3
import typer
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
app = typer.Typer(help="Database backup utility")


class DatabaseBackup:
    """Database backup manager."""
    
    def __init__(self) -> None:
        """Initialize backup manager."""
        self.s3_client = None
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            self.s3_client = boto3.client(
                "s3",
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
    
    def create_backup(
        self,
        output_dir: Optional[Path] = None,
        compress: bool = True,
    ) -> Path:
        """
        Create database backup using pg_dump.
        
        Args:
            output_dir: Directory to save backup
            compress: Whether to compress backup
            
        Returns:
            Path to backup file
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"cerebrum_backup_{timestamp}.sql"
        
        if output_dir:
            output_path = output_dir / filename
        else:
            output_path = Path(filename)
        
        # Build pg_dump command
        cmd = [
            "pg_dump",
            "--host", settings.DB_HOST,
            "--port", str(settings.DB_PORT),
            "--username", settings.DB_USER,
            "--dbname", settings.DB_NAME,
            "--format", "custom",
            "--verbose",
        ]
        
        # Add compression
        if compress:
            cmd.extend(["--compress", "6"])
            filename += ".gz"
            output_path = output_path.with_suffix(".sql.gz")
        
        env = os.environ.copy()
        env["PGPASSWORD"] = settings.DB_PASSWORD
        
        logger.info(
            "Starting database backup",
            database=settings.DB_NAME,
            output=str(output_path),
        )
        
        try:
            with open(output_path, "wb") as f:
                process = subprocess.Popen(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    env=env,
                )
                _, stderr = process.communicate()
                
                if process.returncode != 0:
                    raise RuntimeError(f"pg_dump failed: {stderr.decode()}")
            
            logger.info(
                "Database backup completed",
                output=str(output_path),
                size_bytes=output_path.stat().st_size,
            )
            
            return output_path
            
        except Exception as e:
            logger.error("Backup failed", error=str(e))
            if output_path.exists():
                output_path.unlink()
            raise
    
    async def upload_to_s3(
        self,
        backup_path: Path,
        bucket: Optional[str] = None,
        prefix: Optional[str] = None,
    ) -> str:
        """
        Upload backup to S3.
        
        Args:
            backup_path: Path to backup file
            bucket: S3 bucket name
            prefix: S3 key prefix
            
        Returns:
            S3 URL of uploaded file
        """
        if not self.s3_client:
            raise RuntimeError("S3 client not configured")
        
        bucket = bucket or settings.S3_BUCKET_NAME
        prefix = prefix or settings.S3_BACKUP_PREFIX
        
        if not bucket:
            raise ValueError("S3 bucket not configured")
        
        key = f"{prefix}{backup_path.name}"
        
        logger.info(
            "Uploading backup to S3",
            bucket=bucket,
            key=key,
        )
        
        try:
            self.s3_client.upload_file(
                str(backup_path),
                bucket,
                key,
                ExtraArgs={
                    "ServerSideEncryption": "AES256",
                    "StorageClass": "STANDARD_IA",  # Infrequent access
                },
            )
            
            s3_url = f"s3://{bucket}/{key}"
            
            logger.info(
                "Backup uploaded to S3",
                url=s3_url,
            )
            
            return s3_url
            
        except ClientError as e:
            logger.error("S3 upload failed", error=str(e))
            raise
    
    async def cleanup_old_backups(
        self,
        retention_days: int = 30,
        bucket: Optional[str] = None,
        prefix: Optional[str] = None,
    ) -> int:
        """
        Clean up old backups based on retention policy.
        
        Args:
            retention_days: Number of days to retain backups
            bucket: S3 bucket name
            prefix: S3 key prefix
            
        Returns:
            Number of deleted backups
        """
        if not self.s3_client:
            logger.warning("S3 client not configured, skipping cleanup")
            return 0
        
        bucket = bucket or settings.S3_BUCKET_NAME
        prefix = prefix or settings.S3_BACKUP_PREFIX
        
        if not bucket:
            logger.warning("S3 bucket not configured, skipping cleanup")
            return 0
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        logger.info(
            "Cleaning up old backups",
            retention_days=retention_days,
            cutoff=cutoff_date.isoformat(),
        )
        
        try:
            # List objects
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
            )
            
            if "Contents" not in response:
                logger.info("No backups found to clean up")
                return 0
            
            deleted_count = 0
            objects_to_delete = []
            
            for obj in response["Contents"]:
                if obj["LastModified"].replace(tzinfo=None) < cutoff_date:
                    objects_to_delete.append({"Key": obj["Key"]})
                    deleted_count += 1
            
            if objects_to_delete:
                self.s3_client.delete_objects(
                    Bucket=bucket,
                    Delete={"Objects": objects_to_delete},
                )
            
            logger.info(
                "Cleanup completed",
                deleted=deleted_count,
            )
            
            return deleted_count
            
        except ClientError as e:
            logger.error("Cleanup failed", error=str(e))
            raise
    
    async def list_backups(
        self,
        bucket: Optional[str] = None,
        prefix: Optional[str] = None,
    ) -> list:
        """
        List available backups in S3.
        
        Args:
            bucket: S3 bucket name
            prefix: S3 key prefix
            
        Returns:
            List of backup objects
        """
        if not self.s3_client:
            raise RuntimeError("S3 client not configured")
        
        bucket = bucket or settings.S3_BUCKET_NAME
        prefix = prefix or settings.S3_BACKUP_PREFIX
        
        if not bucket:
            raise ValueError("S3 bucket not configured")
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
            )
            
            return response.get("Contents", [])
            
        except ClientError as e:
            logger.error("Failed to list backups", error=str(e))
            raise
    
    async def restore_backup(
        self,
        backup_path: Path,
        target_db: Optional[str] = None,
    ) -> None:
        """
        Restore database from backup.
        
        WARNING: This will overwrite existing data!
        
        Args:
            backup_path: Path to backup file
            target_db: Target database name
        """
        target_db = target_db or settings.DB_NAME
        
        logger.warning(
            "Restoring database - existing data will be overwritten!",
            target=target_db,
            backup=str(backup_path),
        )
        
        # Build pg_restore command
        cmd = [
            "pg_restore",
            "--host", settings.DB_HOST,
            "--port", str(settings.DB_PORT),
            "--username", settings.DB_USER,
            "--dbname", target_db,
            "--verbose",
            "--clean",  # Clean objects before recreating
            "--if-exists",
            str(backup_path),
        ]
        
        env = os.environ.copy()
        env["PGPASSWORD"] = settings.DB_PASSWORD
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            stdout, stderr = process.communicate()
            
            if process.returncode not in [0, 1]:  # 1 is warning
                raise RuntimeError(f"pg_restore failed: {stderr.decode()}")
            
            logger.info("Database restore completed")
            
        except Exception as e:
            logger.error("Restore failed", error=str(e))
            raise


@app.command()
def backup(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    upload: bool = typer.Option(True, "--upload/--no-upload", help="Upload to S3"),
    cleanup: bool = typer.Option(True, "--cleanup/--no-cleanup", help="Clean up old backups"),
    retention: int = typer.Option(30, "--retention", "-r", help="Retention days"),
) -> None:
    """
    Create and upload database backup.
    
    Args:
        output: Output directory for local backup
        upload: Whether to upload to S3
        cleanup: Whether to clean up old backups
        retention: Backup retention in days
    """
    async def run():
        backup_manager = DatabaseBackup()
        
        # Create backup
        backup_path = backup_manager.create_backup(output_dir=output)
        typer.echo(f"Backup created: {backup_path}")
        
        # Upload to S3
        if upload and backup_manager.s3_client:
            try:
                s3_url = await backup_manager.upload_to_s3(backup_path)
                typer.echo(f"Backup uploaded: {s3_url}")
            except Exception as e:
                typer.echo(f"Upload failed: {e}", err=True)
        
        # Clean up old backups
        if cleanup:
            try:
                deleted = await backup_manager.cleanup_old_backups(retention_days=retention)
                typer.echo(f"Cleaned up {deleted} old backups")
            except Exception as e:
                typer.echo(f"Cleanup failed: {e}", err=True)
    
    asyncio.run(run())


@app.command()
def list_backups(
    bucket: Optional[str] = typer.Option(None, "--bucket", "-b", help="S3 bucket"),
) -> None:
    """List available backups in S3."""
    async def run():
        backup_manager = DatabaseBackup()
        
        if not backup_manager.s3_client:
            typer.echo("S3 not configured", err=True)
            raise typer.Exit(1)
        
        try:
            backups = await backup_manager.list_backups(bucket=bucket)
            
            if not backups:
                typer.echo("No backups found")
                return
            
            typer.echo(f"{'Name':<50} {'Size':>15} {'Modified':<25}")
            typer.echo("-" * 95)
            
            for backup in sorted(backups, key=lambda x: x["LastModified"], reverse=True):
                name = backup["Key"].split("/")[-1]
                size = backup["Size"]
                modified = backup["LastModified"].strftime("%Y-%m-%d %H:%M:%S")
                
                typer.echo(f"{name:<50} {size:>15,} {modified:<25}")
                
        except Exception as e:
            typer.echo(f"Failed to list backups: {e}", err=True)
            raise typer.Exit(1)
    
    asyncio.run(run())


@app.command()
def restore(
    backup_file: Path = typer.Argument(..., help="Backup file path"),
    target_db: Optional[str] = typer.Option(None, "--target-db", "-t", help="Target database"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """
    Restore database from backup.
    
    WARNING: This will overwrite existing data!
    
    Args:
        backup_file: Path to backup file
        target_db: Target database name
        force: Skip confirmation prompt
    """
    if not force:
        confirm = typer.confirm(
            f"This will OVERWRITE database '{target_db or settings.DB_NAME}'. Continue?"
        )
        if not confirm:
            typer.echo("Restore cancelled")
            raise typer.Exit(0)
    
    async def run():
        backup_manager = DatabaseBackup()
        
        try:
            await backup_manager.restore_backup(backup_file, target_db=target_db)
            typer.echo("Restore completed successfully")
        except Exception as e:
            typer.echo(f"Restore failed: {e}", err=True)
            raise typer.Exit(1)
    
    asyncio.run(run())


if __name__ == "__main__":
    app()
