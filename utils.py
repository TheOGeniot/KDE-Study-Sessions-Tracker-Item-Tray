#!/usr/bin/env python3
import socket
import time
from typing import Tuple

def check_connectivity(host: str = "8.8.8.8", port: int = 53, timeout: float = 1.0) -> Tuple[bool, float]:
    """
    Try TCP connect to host:port with a timeout.
    Returns (reachable, latency_ms). latency_ms is -1 if not reachable.
    """
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            latency = (time.time() - start) * 1000.0
            return True, latency
    except Exception:
        return False, -1.0
