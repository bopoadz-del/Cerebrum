"""
Database Seeding Script

Initializes the database with required data including:
- Default roles and permissions
- Admin user
- Sample projects (optional)
"""

import asyncio
import uuid
from datetime import datetime

import typer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security.password import PasswordManager
from app.db.base_class import Base
from app.db.session import db_manager, get_db_context
from app.models.user import User, Role

logger = get_logger(__name__)
app = typer.Typer(help="Database seeding utility")


class DatabaseSeeder:
    """Database seeder for initial data."""
    
    def __init__(self) -> None:
        """Initialize seeder."""
        self.password_manager = PasswordManager()
    
    async def seed_all(self, create_sample_data: bool = False) -> None:
        """
        Seed all required data.
        
        Args:
            create_sample_data: Whether to create sample projects
        """
        logger.info("Starting database seeding")
        
        async with get_db_context() as db:
            await self.seed_roles(db)
            await self.seed_admin_user(db)
            
            if create_sample_data:
                await self.seed_sample_data(db)
        
        logger.info("Database seeding completed")
    
    async def seed_roles(self, db: AsyncSession) -> None:
        """
        Seed default roles.
        
        Args:
            db: Database session
        """
        logger.info("Seeding roles")
        
        roles = [
            {
                "name": "superadmin",
                "description": "System super administrator with full access",
                "permissions": ["*"],
                "is_system": True,
            },
            {
                "name": "admin",
                "description": "Organization administrator",
                "permissions": [
                    "users:read", "users:write", "users:delete",
                    "projects:read", "projects:write", "projects:delete",
                    "settings:read", "settings:write",
                ],
                "is_system": True,
            },
            {
                "name": "manager",
                "description": "Project manager",
                "permissions": [
                    "users:read",
                    "projects:read", "projects:write",
                    "tasks:read", "tasks:write",
                ],
                "is_system": True,
            },
            {
                "name": "user",
                "description": "Standard user",
                "permissions": [
                    "projects:read",
                    "tasks:read", "tasks:write",
                ],
                "is_system": True,
            },
            {
                "name": "viewer",
                "description": "Read-only user",
                "permissions": ["projects:read", "tasks:read"],
                "is_system": True,
            },
        ]
        
        for role_data in roles:
            # Check if role exists
            result = await db.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.debug(f"Role already exists: {role_data['name']}")
                continue
            
            role = Role(
                id=uuid.uuid4(),
                name=role_data["name"],
                description=role_data["description"],
                permissions=role_data["permissions"],
                is_system=role_data["is_system"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(role)
            logger.info(f"Created role: {role_data['name']}")
        
        await db.commit()
        logger.info("Roles seeded successfully")
    
    async def seed_admin_user(self, db: AsyncSession) -> None:
        """
        Seed admin user from environment variables.
        
        Args:
            db: Database session
        """
        logger.info("Seeding admin user")
        
        # Get admin credentials from environment
        admin_email = settings.ADMIN_EMAIL if hasattr(settings, 'ADMIN_EMAIL') else "admin@cerebrum.ai"
        admin_password = settings.ADMIN_PASSWORD if hasattr(settings, 'ADMIN_PASSWORD') else None
        
        if not admin_password:
            logger.warning("ADMIN_PASSWORD not set, skipping admin user creation")
            logger.info("Set ADMIN_EMAIL and ADMIN_PASSWORD to create admin user")
            return
        
        # Check if admin exists
        result = await db.execute(
            select(User).where(User.email == admin_email)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.info(f"Admin user already exists: {admin_email}")
            return
        
        # Hash password
        hashed_password = self.password_manager.hash(admin_password)
        
        # Get superadmin role
        result = await db.execute(
            select(Role).where(Role.name == "superadmin")
        )
        superadmin_role = result.scalar_one_or_none()
        
        # Create admin user
        admin = User(
            id=uuid.uuid4(),
            email=admin_email,
            hashed_password=hashed_password,
            full_name="System Administrator",
            role="superadmin",
            tenant_id=uuid.uuid4(),  # Create system tenant
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        db.add(admin)
        await db.flush()  # Get the user ID
        
        # Assign superadmin role
        if superadmin_role:
            admin.roles.append(superadmin_role)
        
        await db.commit()
        
        logger.info(f"Created admin user: {admin_email}")
        logger.info(f"Admin tenant ID: {admin.tenant_id}")
    
    async def seed_sample_data(self, db: AsyncSession) -> None:
        """
        Seed sample projects and data.
        
        Args:
            db: Database session
        """
        logger.info("Seeding sample data")
        
        # This is where you'd add sample projects, tasks, etc.
        # Example:
        # sample_projects = [
        #     {"name": "Sample Project 1", "description": "..."},
        #     {"name": "Sample Project 2", "description": "..."},
        # ]
        
        logger.info("Sample data seeded")
    
    async def reset_database(self) -> None:
        """Reset database - drops and recreates all tables."""
        logger.warning("Resetting database - all data will be lost!")
        
        # Initialize database connection
        db_manager.initialize()
        
        async with db_manager.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database reset completed")


@app.command()
def seed(
    reset: bool = typer.Option(False, "--reset", help="Reset database before seeding"),
    sample: bool = typer.Option(False, "--sample", help="Create sample data"),
) -> None:
    """
    Seed the database with initial data.
    
    Args:
        reset: Whether to reset database first
        sample: Whether to create sample data
    """
    async def run():
        seeder = DatabaseSeeder()
        
        # Initialize database
        db_manager.initialize()
        
        if reset:
            await seeder.reset_database()
        
        await seeder.seed_all(create_sample_data=sample)
        
        # Close connections
        await db_manager.close()
    
    asyncio.run(run())
    typer.echo("Seeding completed successfully!")


@app.command()
def create_admin(
    email: str = typer.Argument(..., help="Admin email"),
    password: str = typer.Argument(..., help="Admin password"),
    full_name: str = typer.Option("System Administrator", help="Full name"),
) -> None:
    """
    Create a new admin user.
    
    Args:
        email: Admin email address
        password: Admin password
        full_name: Admin full name
    """
    async def run():
        db_manager.initialize()
        
        async with get_db_context() as db:
            seeder = DatabaseSeeder()
            
            # Check if user exists
            result = await db.execute(
                select(User).where(User.email == email)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                typer.echo(f"User already exists: {email}")
                return
            
            # Get superadmin role
            result = await db.execute(
                select(Role).where(Role.name == "superadmin")
            )
            superadmin_role = result.scalar_one_or_none()
            
            # Create admin
            hashed_password = seeder.password_manager.hash(password)
            
            admin = User(
                id=uuid.uuid4(),
                email=email,
                hashed_password=hashed_password,
                full_name=full_name,
                role="superadmin",
                tenant_id=uuid.uuid4(),
                is_active=True,
                is_verified=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            db.add(admin)
            await db.flush()
            
            if superadmin_role:
                admin.roles.append(superadmin_role)
            
            await db.commit()
            
            typer.echo(f"Admin user created: {email}")
            typer.echo(f"Tenant ID: {admin.tenant_id}")
        
        await db_manager.close()
    
    asyncio.run(run())


if __name__ == "__main__":
    app()
