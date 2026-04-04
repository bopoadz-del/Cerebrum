"""
PgBouncer Configuration Manager

Provides configuration and connection management for PgBouncer
connection pooler to optimize PostgreSQL connection handling.
"""

import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PgBouncerConfig:
    """PgBouncer configuration parameters."""
    
    # Pool settings
    pool_mode: str = "transaction"  # transaction, session, or statement
    max_client_conn: int = 10000
    default_pool_size: int = 20
    min_pool_size: int = 5
    reserve_pool_size: int = 5
    reserve_pool_timeout: int = 3
    max_db_connections: int = 100
    max_user_connections: int = 100
    
    # Connection settings
    server_idle_timeout: int = 600
    server_lifetime: int = 3600
    server_connect_timeout: int = 15
    server_login_retry: int = 15
    
    # Query timeout settings
    query_timeout: int = 0  # 0 = disabled
    query_wait_timeout: int = 120
    client_idle_timeout: int = 0  # 0 = disabled
    client_login_timeout: int = 60
    
    # Logging settings
    log_connections: bool = True
    log_disconnections: bool = True
    log_pooler_errors: bool = True
    stats_period: int = 60
    
    # Admin settings
    admin_users: str = "postgres"
    stats_users: str = "stats, postgres"


class PgBouncerManager:
    """
    Manages PgBouncer configuration and connection strings.
    
    Provides utilities for generating PgBouncer configuration files
    and managing connection pool settings.
    """
    
    def __init__(self, config: Optional[PgBouncerConfig] = None) -> None:
        """
        Initialize PgBouncer manager.
        
        Args:
            config: PgBouncer configuration, uses defaults if not provided
        """
        self.config = config or PgBouncerConfig()
        
    def generate_config(self) -> str:
        """
        Generate PgBouncer configuration file content.
        
        Returns:
            Complete pgbouncer.ini configuration as string
        """
        config = textwrap.dedent(f"""\
            ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
            ; PgBouncer Configuration for Cerebrum AI Platform
            ; Auto-generated - Do not edit manually
            ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
            
            [databases]
            ; Database connections
            cerebrum = host={settings.DB_HOST} port={settings.DB_PORT} dbname={settings.DB_NAME}
            
            [pgbouncer]
            ; Connection settings
            listen_addr = 0.0.0.0
            listen_port = 6432
            auth_type = scram-sha-256
            auth_file = /etc/pgbouncer/userlist.txt
            
            ; Pool settings
            pool_mode = {self.config.pool_mode}
            max_client_conn = {self.config.max_client_conn}
            default_pool_size = {self.config.default_pool_size}
            min_pool_size = {self.config.min_pool_size}
            reserve_pool_size = {self.config.reserve_pool_size}
            reserve_pool_timeout = {self.config.reserve_pool_timeout}
            max_db_connections = {self.config.max_db_connections}
            max_user_connections = {self.config.max_user_connections}
            
            ; Connection lifecycle
            server_idle_timeout = {self.config.server_idle_timeout}
            server_lifetime = {self.config.server_lifetime}
            server_connect_timeout = {self.config.server_connect_timeout}
            server_login_retry = {self.config.server_login_retry}
            
            ; Query settings
            query_timeout = {self.config.query_timeout}
            query_wait_timeout = {self.config.query_wait_timeout}
            client_idle_timeout = {self.config.client_idle_timeout}
            client_login_timeout = {self.config.client_login_timeout}
            
            ; Logging
            log_connections = {int(self.config.log_connections)}
            log_disconnections = {int(self.config.log_disconnections)}
            log_pooler_errors = {int(self.config.log_pooler_errors)}
            stats_period = {self.config.stats_period}
            
            ; Admin
            admin_users = {self.config.admin_users}
            stats_users = {self.config.stats_users}
            
            ; TLS settings (production)
            ; client_tls_sslmode = require
            ; client_tls_key_file = /etc/pgbouncer/server.key
            ; client_tls_cert_file = /etc/pgbouncer/server.crt
            ; client_tls_ca_file = /etc/pgbouncer/ca.crt
            
            ; Performance tuning
            tcp_keepalive = 1
            tcp_keepcnt = 3
            tcp_keepidle = 30
            tcp_keepintvl = 10
            
            ; Memory settings
            pkt_buf = 8192
            max_packet_size = 2147483647
            
            ; DNS settings
            dns_max_ttl = 15
            dns_nxdomain_ttl = 15
            dns_zone_check_period = 0
            
            ; Misc
            application_name_add_host = 1
            unix_socket_dir = /tmp
        """)
        
        return config
    
    def generate_userlist(self, users: dict[str, str]) -> str:
        """
        Generate PgBouncer userlist.txt content.
        
        Args:
            users: Dictionary of username -> password pairs
            
        Returns:
            Userlist content as string
        """
        lines = ["; PgBouncer userlist - Auto-generated"]
        for username, password in users.items():
            lines.append(f'"{username}" "{password}"')
        return "\n".join(lines)
    
    def get_pgbouncer_url(
        self,
        original_url: Optional[str] = None,
        use_pgbouncer: bool = True,
    ) -> str:
        """
        Convert database URL to use PgBouncer.
        
        Args:
            original_url: Original database URL
            use_pgbouncer: Whether to use PgBouncer
            
        Returns:
            Modified URL pointing to PgBouncer if enabled
        """
        if not use_pgbouncer:
            return original_url or settings.DATABASE_URL
        
        url = original_url or settings.DATABASE_URL
        
        # Replace port and host for PgBouncer
        # Default PgBouncer listens on port 6432
        pgbouncer_host = settings.PGBOUNCER_HOST or settings.DB_HOST
        pgbouncer_port = settings.PGBOUNCER_PORT or 6432
        
        # Simple URL transformation
        import re
        url = re.sub(
            r"@(.*?):(\d+)/",
            f"@{pgbouncer_host}:{pgbouncer_port}/",
            url,
        )
        
        logger.debug(
            "Converted to PgBouncer URL",
            host=pgbouncer_host,
            port=pgbouncer_port,
        )
        
        return url
    
    def write_config(self, output_path: Path) -> None:
        """
        Write PgBouncer configuration to file.
        
        Args:
            output_path: Path to write configuration
        """
        config = self.generate_config()
        output_path.write_text(config)
        logger.info("PgBouncer config written", path=str(output_path))
    
    def write_userlist(self, users: dict[str, str], output_path: Path) -> None:
        """
        Write userlist to file.
        
        Args:
            users: Dictionary of username -> password pairs
            output_path: Path to write userlist
        """
        userlist = self.generate_userlist(users)
        output_path.write_text(userlist)
        logger.info("PgBouncer userlist written", path=str(output_path))


# Default PgBouncer manager instance
pgbouncer = PgBouncerManager()


def get_pgbouncer_stats_command() -> str:
    """
    Get command to query PgBouncer statistics.
    
    Returns:
        psql command for PgBouncer stats
    """
    return (
        f"psql -h {settings.PGBOUNCER_HOST or settings.DB_HOST} "
        f"-p {settings.PGBOUNCER_PORT or 6432} "
        f"-U {settings.DB_USER} pgbouncer -c 'SHOW STATS;'"
    )


def get_pgbouncer_pools_command() -> str:
    """
    Get command to query PgBouncer pool status.
    
    Returns:
        psql command for PgBouncer pools
    """
    return (
        f"psql -h {settings.PGBOUNCER_HOST or settings.DB_HOST} "
        f"-p {settings.PGBOUNCER_PORT or 6432} "
        f"-U {settings.DB_USER} pgbouncer -c 'SHOW POOLS;'"
    )
