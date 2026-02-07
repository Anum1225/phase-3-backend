from sqlalchemy import text
from db import engine

def migrate():
    with engine.connect() as conn:
        print("Migrating task table...")
        try:
            # Add columns efficiently. IF NOT EXISTS is supported in Postgres 9.6+
            conn.execute(text("ALTER TABLE task ADD COLUMN IF NOT EXISTS due_date TIMESTAMP WITHOUT TIME ZONE"))
            conn.execute(text("ALTER TABLE task ADD COLUMN IF NOT EXISTS is_recurring BOOLEAN DEFAULT FALSE NOT NULL"))
            conn.execute(text("ALTER TABLE task ADD COLUMN IF NOT EXISTS recurring_interval VARCHAR(50)"))
            conn.execute(text("ALTER TABLE task ADD COLUMN IF NOT EXISTS reminder_at TIMESTAMP WITHOUT TIME ZONE"))
            conn.commit()
            print("Migration successful! Added new task columns.")
        except Exception as e:
            # Log error but don't crash if it's just that columns exist (handled by IF NOT EXISTS usually, but good to be safe)
            print(f"Migration message: {e}")

if __name__ == "__main__":
    migrate()
