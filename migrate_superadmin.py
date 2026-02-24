"""Migration script to add Election and Candidate tables and update User model."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from app.config import get_settings
from app.database import Base
from app.models import User, Candidate, Election

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)

def migrate():
    """Run migration to add new tables and columns."""
    print("Starting migration...")
    
    with engine.connect() as conn:
        # Add new columns to users table
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN id_number VARCHAR(50)"))
            print("✓ Added id_number column")
        except:
            print("- id_number column already exists")
        
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN reg_number VARCHAR(50)"))
            print("✓ Added reg_number column")
        except:
            print("- reg_number column already exists")
        
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR(255)"))
            print("✓ Added full_name column")
        except:
            print("- full_name column already exists")
        
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20)"))
            print("✓ Added phone column")
        except:
            print("- phone column already exists")
        
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN address TEXT"))
            print("✓ Added address column")
        except:
            print("- address column already exists")
        
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN custom_fields JSON"))
            print("✓ Added custom_fields column")
        except:
            print("- custom_fields column already exists")
        
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_deletable BOOLEAN DEFAULT 1"))
            print("✓ Added is_deletable column")
        except:
            print("- is_deletable column already exists")
        
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN created_by INTEGER"))
            print("✓ Added created_by column")
        except:
            print("- created_by column already exists")
        
        conn.commit()
    
    # Create new tables
    print("\nCreating new tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ All tables created/updated")
    
    # Mark superadmin as non-deletable
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "UPDATE users SET is_deletable = 0 WHERE role = 'superadmin'"
            ))
            conn.commit()
            print("✓ Marked superadmin as non-deletable")
        except Exception as e:
            print(f"- Could not update superadmin: {e}")
    
    print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    migrate()
