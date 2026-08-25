import sys
import os

# Ensure the project root is in the Python path so that
# app.py, config.py, routes/, models/, etc. can be imported
# when running inside Vercel's serverless function environment.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app