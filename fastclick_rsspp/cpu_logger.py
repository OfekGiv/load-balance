#!/usr/bin/env python3
import argparse
import csv
import re
import socket
import sys
import time
from typing import List, Optional, Tuple

# ------------------------- ControlSocket helpers -------------------------

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")

def _read_handler(host: str, port: int, expr: str, timeout: float = 1.0) -> Optional[List[float]]:
    """
    READ <expr> from Click ControlSocket and return a list of numbers parsed
    from the first data line after 'DATA N'. Falls back to last non-empty line.
    Returns None on failure.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.sendall(f"READ {expr}\n".encode("ascii"))
            s.shutdown(socket.SHUT_WR)
            s.settimeout(timeout)
            buf = bytearray()
            while True:
                try:
                    chunk = s.recv(4096)
                except socket.timeout:
                    break
                if not chunk:
                    break
                buf.extend(chunk)
        if not buf:
            return None
        text = buf.decode("utf-8", errors="replace")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        # Try to find the line after "DATA N"
        for i, ln in enumerate(lines):
            if ln.startswith("DATA"):
                tgt = lines[i + 1] if i + 1 < len(lines) else ""
                nums = _NUM_RE.findall(tgt)
                if nums:
                    return [float(x) for x in nums]
                break
        # Fallback: parse last non-empty line
        nums = _NUM_RE.findall(lines[-1])
        if nums:
            return [float(x) for x in nums]
        return None
    except Exception:
        return None

def read_load_once(host: str, port: int, timeout: float = 1.0) -> Optional[List[float]]:
    """Return per-core loads (0..1 floats) or None."""
    return _read_handler(host, port, "load", timeout)

def read_counter(host: str, port: int, handler: str, timeout: float = 1.0) -> Optional[int]:
    """Read a single integer counter (e.g., c_in.count or in.hw_count)."""
    vals = _read_handler(host, port, handler, timeout)
    if not vals:
        return None
    # Take the first value; Click count handlers return a single number
    return int(vals[0])

# ------------------------- Main logic -------------------------

def main():
    ap = argparse.ArgumentParser(description="Log Click per-core load + throughput (pps/Gbps) to CSV")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1234)
    ap.add_argument("--duration", type=float, default=20.0, help="seconds to run")
    ap.add_argument("--interval", type=float, default=1.0, help="sampling interval (s)")
    ap.add_argument("--out", default="cpu_load_wide.csv")
    ap.add_argument("--append", action="store_true", help="append to existing file without rewriting header")
    # Throughput sources (pick what you have)
    ap.add_argument("--pkt-handler", default=None,
                    help="Handler name for packet counter (e.g., 'c_in.count' or 'in.hw_count')")
    ap.add_argument("--byte-handler", default=None,
                    help="Handler name for byte counter (e.g., 'c_in.byte_count' or 'in.hw_bytes')")
    args = ap.parse_args()

    # First sample (loads)
    loads0 = read_load_once(args.host, args.port)
    if not loads0:
        print(f"ERROR: Could not read 'load' from {args.host}:{args.port}", file=sys.stderr)
        sys.exit(2)

    # Optional first counters
    pkt0: Optional[int] = None
    byt0: Optional[int] = None
    if args.pkt_handler:
        pkt0 = read_counter(args.host, args.port, args.pkt_handler)
        if pkt0 is None:
            print(f"WARNING: could not read '{args.pkt_handler}' (pps will be empty)", file=sys.stderr)
    if args.byte_handler:
        byt0 = read_counter(args.host, args.port, args.byte_handler)
        if byt0 is None:
            print(f"WARNING: could not read '{args.byte_handler}' (gbps will be empty)", file=sys.stderr)

    # CSV header prepare
    cpu_cols = [f"cpu{i}" for i in range(len(loads0))]
    header = ["ts"] + cpu_cols
    if args.pkt_handler:
        header.append("pps")
    if args.byte_handler:
        header.append("gbps")

    # Open CSV (append or write)
    write_header = True
    if args.append:
        try:
            with open(args.out, "r", newline="") as f:
                if f.read(1):
                    write_header = False
        except FileNotFoundError:
            write_header = True

    # Timing: wall time for CSV, monotonic for Δt
    t_csv = time.time()
    t_mon = time.monotonic()

    with open(args.out, "a" if args.append else "w", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(header)

        # Write first row
        row = [f"{t_csv:.3f}"] + [round(v * 100.0, 1) for v in loads0]
        # No rates on the very first line (need a delta)
        if args.pkt_handler:
            row.append("")  # pps placeholder
        if args.byte_handler:
            row.append("")  # gbps placeholder
        w.writerow(row); f.flush()

        # Loop
        end_mon = t_mon + args.duration
        prev_pkt = pkt0
        prev_byt = byt0
        prev_mon = t_mon

        while time.monotonic() < end_mon:
            t_loop_start = time.monotonic()

            loads = read_load_once(args.host, args.port)
            if loads:
                # pad/truncate if CPU count changes
                if len(loads) < len(cpu_cols):
                    loads = loads + [0.0] * (len(cpu_cols) - len(loads))
                elif len(loads) > len(cpu_cols):
                    loads = loads[:len(cpu_cols)]

            pkt = read_counter(args.host, args.port, args.pkt_handler, 0.5) if args.pkt_handler else None
            byt = read_counter(args.host, args.port, args.byte_handler, 0.5) if args.byte_handler else None

            now_csv = time.time()
            now_mon = time.monotonic()
            dt = max(1e-6, now_mon - prev_mon)  # protect div0

            # Compute rates
            pps = ""
            gbps = ""
            if args.pkt_handler and (pkt is not None) and (prev_pkt is not None):
                dp = pkt - prev_pkt
                if dp < 0:  # counter reset/wrap
                    dp = 0
                pps = f"{dp / dt:.3f}"
            if args.byte_handler and (byt is not None) and (prev_byt is not None):
                db = byt - prev_byt
                if db < 0:
                    db = 0
                gbps = f"{8.0 * db / dt / 1e9:.6f}"

            # Build row
            out_loads = [round(v * 100.0, 1) for v in (loads or loads0)]
            row = [f"{now_csv:.3f}"] + out_loads
            if args.pkt_handler:
                row.append(pps)
            if args.byte_handler:
                row.append(gbps)
            w.writerow(row); f.flush()

            # Update prevs
            if pkt is not None:
                prev_pkt = pkt
            if byt is not None:
                prev_byt = byt
            prev_mon = now_mon

            # Sleep remaining
            elapsed = time.monotonic() - t_loop_start
            to_sleep = args.interval - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)

if __name__ == "__main__":
    main()

