#!/usr/bin/env python3
"""
CacheForge Standalone Entrypoint Executable.
Allows running cacheforge directly without package installation.
"""

import sys
from cacheforge.cli import main

if __name__ == "__main__":
    sys.exit(main())
