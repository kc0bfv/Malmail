"""
Common functionality potentially required by every module
"""

import sys

def print_error(*args):
    """Print an error nicely."""
    print(*args, file=sys.stderr)#, flush=True)
    sys.stderr.flush()
