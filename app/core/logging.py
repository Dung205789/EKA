import logging
from app.core.config import settings

def setup_logging():
    level = logging.DEBUG if settings.ENV != "prod" else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
