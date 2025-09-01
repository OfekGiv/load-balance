#!/usr/bin/env python3
import socket, time

HOST = "127.0.0.1"
PORT = 1234 
ELEMENTS = ["fd0", "fd1"]  # your FromDPDKDevice elements
HANDLERS = ["queue_stats", "xstats", "stats"]

def send(sock, cmd):
    sock.sendall((cmd + "\n").encode())
    data = b""
    sock.settimeout(2.0)
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
        if b"\n" in chunk:  # simple line-oriented framing
            break
    return data.decode(errors="ignore").strip()

with socket.create_connection((HOST, PORT)) as s:
    # pick a working handler by probing the first element
    chosen = None
    for h in HANDLERS:
        resp = send(s, f"READ {ELEMENTS[0]}.{h}")
        if resp.startswith("200"):
            chosen = h
            break
    if not chosen:
        raise SystemExit("No supported handler found (tried: %s)" % HANDLERS)

    print(f"Using handler: {chosen}")
    for el in ELEMENTS:
        resp = send(s, f"READ {el}.{chosen}")
        print(f"=== {el} ({chosen}) ===")
        for line in resp.splitlines():
            if line.startswith("DATA "):
                print(line[5:])
        print()
        time.sleep(1)

