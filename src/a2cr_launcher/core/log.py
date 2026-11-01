import logging


def get_logger(name) -> logging.Logger:
    return logging.getLogger(f"a2cr.{name}")
