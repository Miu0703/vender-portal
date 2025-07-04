import os
import logging
from app import create_app
from app.config import Config

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT,
    datefmt=Config.LOG_DATE_FORMAT
)

# Create upload directory
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

app = create_app()

if __name__ == "__main__":
    # Run in development environment
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    ) 