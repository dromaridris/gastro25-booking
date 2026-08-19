"""Standard application logging configuration."""

import logging
import sys


def configure_logging(app):
    level = logging.DEBUG if app.debug else logging.INFO
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
        root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("werkzeug").setLevel(logging.WARNING if not app.debug else logging.INFO)
    app.logger.setLevel(level)
