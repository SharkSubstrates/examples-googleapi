"""
GDrive Kit - Google Drive API toolkit
"""
import logging

# Configure logging once for the entire package
# Only show WARNING and above for all loggers
logging.basicConfig(
    level=logging.WARNING,
    format='%(name)s - %(levelname)s - %(message)s'
)

# Suppress noisy third-party libraries
logging.getLogger('googleapiclient').setLevel(logging.ERROR)
logging.getLogger('google_auth_httplib2').setLevel(logging.ERROR)
logging.getLogger('google.auth').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)

