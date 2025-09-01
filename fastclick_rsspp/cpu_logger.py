#!/usr/bin/env python3
import argparse
import csv
import socket
import sys
import time
from datetime import datetime

def read_load_once(host: str, port: int, timeout: float = 1.0) -> list[float] | None:
    """
    Connects to Click ControlSocket, sends 'READ load', returns list of floats (per-core loads),
    or None on failure.
    Protocol usually returns:
      Click::ControlSocket/1.3
      200 Read handler 'load' OK
      DATA N
      <numbers...>
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.sendall(b"READ load\n")
            s.shutdown(socket.SHUT_WR)  # signal EOF to Click
            s.settimeout(timeout)
            chunks = []
            while True:
                try:
                    data = s.recv(4096)
                except socket.timeout:
                    break
                if not data:
                    break
                chunks.append(data)
        if not chunks:
            return None
        text = b"".join(chunks).decode("utf-8", errors="replace")
        # Find the line after "DATA N"
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for idx, ln in enumerate(lines):
            parts = ln.split()
            if parts and parts[0] == "DATA":
                if idx + 1 < len(lines):
                    # Next line should have numbers
                    nums_line = lines[idx + 1]
                    try:
                        values = [float(x) for x in nums_line.split()]
                        return values
                    except ValueError:
                        return None
                break
        # Fallback: if response is just numbers on last line
        try:
            values = [float(x) for x in lines[-1].split()]
            return values
        except Exception:
            return None
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser(description="Log Click per-core load to wide CSV (ts,cpu0,...)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1234)
    ap.add_argument("--duration", type=float, default=17.0, help="seconds to run")
    ap.add_argument("--interval", type=float, default=0.5, help="sampling interval seconds")
    ap.add_argument("--out", default="cpu_load_wide.csv")
    ap.add_argument("--append", action="store_true", help="append to existing file without rewriting header")
    args = ap.parse_args()

    end_time = time.time() + args.duration
    first = read_load_once(args.host, args.port)
    if not first:
        print(f"ERROR: Could not read 'load' from {args.host}:{args.port}", file=sys.stderr)
        sys.exit(2)

    # Open CSV
    write_header = True
    if args.append:
        try:
            with open(args.out, "r", newline="") as f:
                # if file exists and has content, don't write header
                if f.read(1):
                    write_header = False
        except FileNotFoundError:
            write_header = True

    with open(args.out, "a" if args.append else "w", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            header = ["ts"] + [f"cpu{i}" for i in range(len(first))]
            writer.writerow(header)

        # Write the first sample immediately (using 'first')
        ts = f"{time.time():.3f}"
        row = [ts] + [round(v * 100.0, 1) for v in first]
        writer.writerow(row)
        f.flush()

        # Continue until end_time
        while time.time() < end_time:
            t_start = time.time()
            vals = read_load_once(args.host, args.port)
            if vals:
                ts = f"{time.time():.3f}"
                # if core count changes, extend/truncate to match header length
                if len(vals) < len(first):
                    vals = vals + [0.0]*(len(first)-len(vals))
                elif len(vals) > len(first):
                    # expand header on the fly by rewriting? keep simple: truncate to original width
                    vals = vals[:len(first)]
                row = [ts] + [round(v * 100.0, 1) for v in vals]
                writer.writerow(row)
                f.flush()
            # sleep remaining interval
            elapsed = time.time() - t_start
            sleep_for = args.interval - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)


if __name__ == "__main__":
    main()
