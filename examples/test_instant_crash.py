import sys

print("About to crash immediately!", file=sys.stderr)
raise RuntimeError("Instant crash for testing!")
