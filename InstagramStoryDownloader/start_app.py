#!/usr/bin/env python
import subprocess
import os
import sys

def main():
    # Use the port 8080 instead of 5000 which might be in use
    command = ["gunicorn", "--bind", "0.0.0.0:8080", "--reuse-port", "--reload", "main:app"]
    
    print(f"Starting application on port 8080 with command: {' '.join(command)}")
    process = subprocess.Popen(command)
    
    try:
        process.wait()
    except KeyboardInterrupt:
        print("Stopping application...")
        process.terminate()
        process.wait()
        print("Application stopped.")

if __name__ == "__main__":
    main()