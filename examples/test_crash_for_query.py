import sys
print("Starting program...")
print("About to crash!", file=sys.stderr)
sys.exit(1)
