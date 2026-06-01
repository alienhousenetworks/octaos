import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "test.db")

def migrate():
    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(workflow_tasks)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "task_type" not in columns:
            print("Adding task_type column...")
            cursor.execute("ALTER TABLE workflow_tasks ADD COLUMN task_type VARCHAR")
        
        if "payload" not in columns:
            print("Adding payload column...")
            cursor.execute("ALTER TABLE workflow_tasks ADD COLUMN payload JSON")
            
        if "scheduled_at" not in columns:
            print("Adding scheduled_at column...")
            cursor.execute("ALTER TABLE workflow_tasks ADD COLUMN scheduled_at DATETIME")
            
        conn.commit()
        print("Migration successful.")
    except Exception as e:
        print(f"Error migrating: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
