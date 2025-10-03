import sys

print("Starting program...")
print("About to crash...", file=sys.stderr)
raise RuntimeError("Intentional crash for testing!")
