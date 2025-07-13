# create_tables.py
# This script is intended to be run manually ONCE from the Render shell
# to set up the initial database schema.

import os
from app import app, db

# The app needs to be in an application context to work with the database.
with app.app_context():
    print("Connecting to the database...")
    # The following command inspects your models and creates the
    # corresponding tables in the database if they don't already exist.
    print("Creating all tables...")
    db.create_all()
    print("Tables created successfully.")
