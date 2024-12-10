import os
import sys

INTERP = os.path.expanduser("/home/USERNAME/virtualenv/YOUR_DOMAIN/3.9/bin/python")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.append(os.getcwd())

from app import app as application
