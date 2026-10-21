import socket
import json
import time

UNITY_IP = '127.0.0.1'
UNITY_PORT = 9000
LISTEN_PORT = 5005

listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind(('0.0.0.0', LISTEN_PORT))
listener.settimeout(2.5)

sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
cmd = {"command": "trigger_fault", "fault_code": 104}
sender.sendto(json.dumps(cmd).encode('utf-8'), (UNITY_IP, UNITY_PORT))
sender.close()
print("Sent command:", cmd)

try:
    data, addr = listener.recvfrom(4096)
    print(f"RECV from Unity ({addr}): {data.decode('utf-8')}")
except socket.timeout:
    print("Timeout waiting for Unity reply on 5005.")
finally:
    listener.close()
