"""Database check and repair endpoint"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api.deps import get_db

router = APIRouter()

@router.get("/db-status")
def check_db_status(db: Session = Depends(get_db)):
    """Check database table status"""
    try:
        # Check if table exists
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'google_drive_tokens'
            )
        """))
        table_exists = result.scalar()
        
        # Check alembic version
        try:
            result = db.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
        except:
            version = "unknown"
        
        return {
            "google_drive_tokens_exists": table_exists,
            "alembic_version": version,
            "tables": []
        }
    except Exception as e:
        return {"error": str(e)}

@router.post("/db-fix")
def fix_db(db: Session = Depends(get_db)):
    """Create missing tables"""
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS google_drive_tokens (
                id SERIAL PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                token_type VARCHAR(50) DEFAULT 'Bearer',
                expires_at TIMESTAMP NOT NULL,
                google_email VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                last_used_at TIMESTAMP,
                UNIQUE (user_id)
            )
        """))
        db.commit()
        return {"status": "table created"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
