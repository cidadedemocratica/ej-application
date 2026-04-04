#!/usr/bin/env python
import os
import sys
from django.core.management import execute_from_command_line

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ej.settings")
    sys.path.append("src")
    # This allows easy placement of apps within the interior EJ directory.
    current_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(current_path, "ej"))

    execute_from_command_line(sys.argv)
