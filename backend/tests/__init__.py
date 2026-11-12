"""Unit tests for the conversational parts search agent."""
import sys
from pathlib import Path

# Ensure backend directory is in sys.path so tests can import parts_agent and server
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

