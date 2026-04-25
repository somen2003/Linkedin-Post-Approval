"""Vercel serverless entry point. Re-exports the FastAPI app from main.py."""
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `import main` works.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app  # noqa: F401, E402