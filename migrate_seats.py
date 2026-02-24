"""Migration for election seats and seat aspirants."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from app.config import get_settings
from app.database import Base
from app.models import ElectionSeat, SeatAspirant

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)

def migrate():
    print("🚀 Migrating election seats...")
    
    with engine.connect() as conn:
        # Add seat_id to votes table
        try:
            conn.execute(text("ALTER TABLE votes ADD COLUMN seat_id INTEGER"))
            print("✓ Added seat_id to votes")
        except:
            print("- seat_id already exists")
        
        conn.commit()
    
    # Create new tables
    Base.metadata.create_all(bind=engine)
    print("✓ Created election_seats and seat_aspirants tables")
    
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    migrate()
