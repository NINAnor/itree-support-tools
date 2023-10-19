"""
py-linux-template
=================

A template packagee for Python projects on Windows.
"""

__author__ = "Willeke A'Campo"
__email__ = "willeke.acampo@nina.no"
__version__ = "0.1.0"

import logging

from src.config.config import load_catalog, load_parameters  # noqa

# local imports
from src.config.logger import setup_logging  # noqa

logging.getLogger(__name__).addHandler(logging.NullHandler())
