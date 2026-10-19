import socket
import json
import time
import sys

LABVIEW_LISTEN_PORT = 5005

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", LABVIEW_LISTEN_PORT))
    sock.settimeout(2.0)

    print(f"[{time.strftime('%H:%M:%S')}] PERSISTENT UDP LISTENER ACTIVE ON PORT {LABVIEW_LISTEN_PORT}")
    print("Listening for incoming Unity telemetry (steps, highlights, completion, submissions)...\n")
    sys.stdout.flush()

    start = time.time()
    # Listen for up to 10 minutes
    while time.time() - start < 600:
        try:
            data, addr = sock.recvfrom(4096)
            text = data.decode("utf-8", errors="replace").strip()
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] <<< RECEIVED FROM UNITY: {text}\n")
            sys.stdout.flush()
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Error: {e}")
            break

    sock.close()
    print("Listener finished.")

if __name__ == "__main__":
    main()
