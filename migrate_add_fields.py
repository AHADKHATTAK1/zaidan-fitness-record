"""
Migration script to add new fields to Member table
Run this once to update your existing database
"""
import sqlite3
import os

db_path = 'gym.db'

if not os.path.exists(db_path):
    print(f"Database {db_path} not found!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if columns already exist
cursor.execute("PRAGMA table_info(member)")
columns = [row[1] for row in cursor.fetchall()]

print(f"Existing columns: {columns}")

# Add missing columns
new_columns = {
    'monthly_price': 'FLOAT',
    'cnic': 'VARCHAR(50)',
    'address': 'TEXT',
    'gender': 'VARCHAR(20)',
    'date_of_birth': 'DATE',
    'notes': 'TEXT'
}

for col_name, col_type in new_columns.items():
    if col_name not in columns:
        try:
            cursor.execute(f"ALTER TABLE member ADD COLUMN {col_name} {col_type}")
            print(f"✓ Added column: {col_name}")
        except sqlite3.OperationalError as e:
            print(f"✗ Could not add {col_name}: {e}")
    else:
        print(f"- Column {col_name} already exists")

conn.commit()
conn.close()

print("\n✓ Migration complete!")
print("You can now restart your Flask app.")
