from __future__ import annotations

import re, socket, time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtCore import QObject, Signal

from utils import current_ipv4

class ParsedProxy:
    __slots__ = ("protocol", "host", "port", "username", "password")

    def __init__(self, protocol: str, host: str, port: int,
                 username: str = "", password: str = ""):
        self.protocol = protocol   # "http" | "https" | "socks4" | "socks5"
        self.host     = host
        self.port     = port
        self.username = username
        self.password = password

    @property
    def has_auth(self) -> bool:
        return bool(self.username)

    @property
    def display(self) -> str:
        auth = f"{self.username}:***@" if self.has_auth else ""
        return f"{self.protocol.upper()}  {auth}{self.host}:{self.port}"

# Support: [scheme://][user:pass@]host:port
_PROXY_RE = re.compile(
    r"^(?:(?P<proto>[a-zA-Z0-9+\-.]+)://)?"
    r"(?:(?P<user>[^:@\s]+):(?P<pwd>[^@\s]*)@)?"
    r"(?P<host>[a-zA-Z0-9._\-\[\]]+)"
    r":(?P<port>\d{1,5})$"
)

_PROTO_MAP = {
    "http":    "http",
    "https":   "https",
    "socks":   "socks5",
    "socks4":  "socks4",
    "socks4a": "socks4",
    "socks5":  "socks5",
    "socks5h": "socks5h",
}

PROXY_PING_TIMEOUT = 15.0
PROXY_GEO_URL = (
    "http://ip-api.com/json/{ip}"
    "?fields=status,message,country,countryCode,regionName,city,isp,org,as,timezone,query"
)
PROXY_SELF_GEO_URL = (
    "http://ip-api.com/json/"
    "?fields=status,message,country,countryCode,regionName,city,isp,org,as,timezone,query"
)
PROXY_TEST_ENDPOINTS = (
    ("ip-api", PROXY_SELF_GEO_URL, "ip-api", (5.0, 15.0)),
    ("ipify", "http://api.ipify.org?format=json", "ipify", (5.0, 10.0)),
    ("icanhazip", "http://icanhazip.com", "plain", (5.0, 10.0)),
)
PROXY_REQUEST_HEADERS = {
    "User-Agent": "stalive-proxy-check/1.0",
    "Cache-Control": "no-cache",
}

def parse_proxy(raw: str, default_protocol: str = "http") -> ParsedProxy | None:
    raw = raw.strip()

    if "://" not in raw and raw.count(":") >= 3:
        host, port_str, username, password = raw.split(":", 3)
        host = host.strip()
        username = username.strip()
        password = password.strip()
        try:
            port = int(port_str.strip())
            if not (1 <= port <= 65535):
                return None
        except ValueError:
            return None
        if not host or not username:
            return None
        return ParsedProxy(default_protocol.lower(), host, port, username, password)

    m = _PROXY_RE.match(raw)
    if not m:
        return None

    proto_raw = (m.group("proto") or "").lower()
    proto     = _PROTO_MAP.get(proto_raw, default_protocol.lower())

    host = m.group("host")
    try:
        port = int(m.group("port"))
        if not (1 <= port <= 65535):
            return None
    except ValueError:
        return None

    return ParsedProxy(
        proto, host, port,
        username=m.group("user") or "",
        password=m.group("pwd")  or "",
    )

def _split_batch_text(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[\n,;]+", text) if part.strip()]

def _parse_port_range(raw: str) -> list[int]:
    ports: set[int] = set()
    for part in re.split(r"[,;\s]+", raw):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start, end = int(start_str), int(end_str)
            if start > end:
                start, end = end, start
            ports.update(range(max(1, start), min(65535, end) + 1))
        else:
            port = int(part)
            if 1 <= port <= 65535:
                ports.add(port)
    return sorted(ports)

def _parse_port_target(raw: str) -> tuple[str, str, int, str | None]:
    if ":" in raw:
        parts = raw.rsplit(":", 1)
        host, port_str = parts[0].strip(), parts[1].strip()
    else:
        host, port_str = current_ipv4(), raw

    try:
        port = int(port_str)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        return raw, "", 0, "Invalid port number (1-65535)"

    if not host:
        return raw, "", 0, "Missing host"

    return f"{host}:{port}", host, port, None

def _check_tcp(host: str, port: int, timeout: float) -> tuple[bool, float, str, str]:
    t0 = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            elapsed = (time.monotonic() - t0) * 1000
            return True, elapsed, "", sock.getpeername()[0]
    except socket.timeout:
        return False, (time.monotonic() - t0) * 1000, "Timed out", ""
    except ConnectionRefusedError:
        return False, (time.monotonic() - t0) * 1000, "Connection refused", ""
    except OSError as exc:
        return False, (time.monotonic() - t0) * 1000, str(exc), ""
    except Exception as exc:
        return False, (time.monotonic() - t0) * 1000, str(exc), ""

def _proxy_url(proxy: ParsedProxy, protocol: str | None = None) -> str:
    auth = ""
    if proxy.username:
        auth = f"{proxy.username}:{proxy.password}@"
    return f"{protocol or proxy.protocol}://{auth}{proxy.host}:{proxy.port}"

def _proxy_probe_protocols(proxy: ParsedProxy) -> list[str]:
    if proxy.protocol == "socks5":
        return ["socks5h", "socks5"]
    return [proxy.protocol]

def _extract_probe_payload(resp: requests.Response, kind: str) -> tuple[str, dict, str]:
    try:
        if kind == "ip-api":
            data = resp.json()
            if data.get("status") != "success":
                return "", {}, str(data.get("message", "Geo endpoint failed"))
            return str(data.get("query", "")).strip(), data, ""
        if kind == "ipify":
            data = resp.json()
            return str(data.get("ip", "")).strip(), {}, ""
        if kind == "plain":
            match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", resp.text or "")
            return (match.group(0), {}, "") if match else ("", {}, "No response IP")
    except Exception as exc:
        return "", {}, str(exc)

    return "", {}, "Unsupported response format"

def _short_error(exc: Exception | str) -> str:
    text = str(exc).strip().replace("\n", " ")
    if len(text) > 180:
        return text[:177].rstrip() + "..."
    return text

def _lookup_ip_geo(ip: str) -> dict:
    if not ip:
        return {}
    try:
        resp = requests.get(PROXY_GEO_URL.format(ip=ip), timeout=PROXY_PING_TIMEOUT)
        if resp.status_code != 200:
            return {}
        geo = resp.json()
        if geo.get("status") != "success":
            return {"geo_error": geo.get("message", "Geo lookup failed")}
        return geo
    except Exception as exc:
        return {"geo_error": str(exc)}

def _probe_proxy(proxy: ParsedProxy) -> dict:
    t0 = time.monotonic()
    errors = []

    for probe_protocol in _proxy_probe_protocols(proxy):
        url = _proxy_url(proxy, probe_protocol)
        proxies = {"http": url, "https": url}
        for endpoint_name, endpoint_url, endpoint_kind, timeout in PROXY_TEST_ENDPOINTS:
            try:
                resp = requests.get(
                    endpoint_url,
                    proxies=proxies,
                    timeout=timeout,
                    headers=PROXY_REQUEST_HEADERS,
                )
            except Exception as exc:
                errors.append(f"{endpoint_name}/{probe_protocol}: {_short_error(exc)}")
                continue

            if resp.status_code != 200:
                errors.append(f"{endpoint_name}/{probe_protocol}: HTTP {resp.status_code}")
                continue

            response_ip, geo, parse_error = _extract_probe_payload(resp, endpoint_kind)
            if not response_ip:
                errors.append(
                    f"{endpoint_name}/{probe_protocol}: {parse_error or 'No response IP'}"
                )
                continue

            if not geo:
                geo = _lookup_ip_geo(response_ip)

            elapsed = (time.monotonic() - t0) * 1000
            return {
                "label": proxy.display,
                "alive": True,
                "elapsed_ms": elapsed,
                "response_ip": response_ip,
                "country": geo.get("country", ""),
                "country_code": geo.get("countryCode", ""),
                "region": geo.get("regionName", ""),
                "city": geo.get("city", ""),
                "asn": geo.get("as", ""),
                "isp": geo.get("isp", ""),
                "org": geo.get("org", ""),
                "timezone": geo.get("timezone", ""),
                "info": f"OK via {endpoint_name}/{probe_protocol}",
            }

    error_text = "; ".join(errors[-3:]) if errors else "Probe failed"
    return {
        "label": proxy.display,
        "alive": False,
        "elapsed_ms": (time.monotonic() - t0) * 1000,
        "error": _short_error(error_text),
    }

def _value_or_dash(value) -> str:
    text = str(value or "").strip()
    return text if text else "-"

def _proxy_location(result: dict) -> str:
    country = str(result.get("country", "")).strip()
    country_code = str(result.get("country_code", "")).strip()
    if country and country_code:
        country_label = f"{country} ({country_code})"
    else:
        country_label = country or country_code
    parts = [
        str(result.get("city", "")).strip(),
        str(result.get("region", "")).strip(),
        country_label,
    ]
    return ", ".join(part for part in parts if part) or "-"

def _format_proxy_result_line(result: dict) -> str:
    index = int(result.get("index", 0) or 0)
    prefix = f"{index:02d}" if index else "--"
    alive = result.get("alive")
    if alive is None:
        status = "â³ pending"
    else:
        status = "âœ… alive" if alive else "âŒ dead"
    elapsed = result.get("elapsed_ms", 0.0) or 0.0
    speed = f"{elapsed:.0f} ms" if elapsed > 0 else "-"
    label = _value_or_dash(result.get("label"))
    response_ip = _value_or_dash(result.get("response_ip"))
    asn = _value_or_dash(result.get("asn"))
    isp = _value_or_dash(result.get("isp") or result.get("org"))
    timezone = _value_or_dash(result.get("timezone"))
    info = _value_or_dash(result.get("info") if alive else result.get("error"))
    return (
        f"{prefix} {status} | speed {speed} | {label} | "
        f"IP response {response_ip} | location {_proxy_location(result)} | "
        f"ASN {asn} | ISP {isp} | timezone {timezone} | info {info}"
    )

def _format_port_result_line(result: dict) -> str:
    index = int(result.get("index", 0) or 0)
    prefix = f"{index:02d}" if index else "--"
    target = _value_or_dash(result.get("target"))
    elapsed = result.get("elapsed_ms", 0.0) or 0.0
    speed = f"{elapsed:.0f} ms" if elapsed > 0 else "-"
    if result.get("alive"):
        peer = _value_or_dash(result.get("peer_ip"))
        return f"{prefix} âœ… open | speed {speed} | {target} | peer {peer}"
    return f"{prefix} âŒ closed | speed {speed} | {target} | info {_value_or_dash(result.get('error'))}"

class PortBatchWorker(QObject):
    item_result = Signal(dict)
    progress = Signal(int, int)
    finished = Signal()

    def __init__(
        self,
        targets: list[str],
        timeout: float = 5.0,
        max_workers: int = 64,
        emit_closed: bool = True,
    ):
        super().__init__()
        self._targets = targets
        self._timeout = timeout
        self._max_workers = max(1, max_workers)
        self._emit_closed = emit_closed

    def _check_one(self, idx: int, raw: str) -> dict:
        label, host, port, error = _parse_port_target(raw)
        if error:
            return {
                "index": idx,
                "target": label,
                "alive": False,
                "elapsed_ms": 0.0,
                "error": error,
                "peer_ip": "",
            }
        ok, elapsed, err, peer_ip = _check_tcp(host, port, self._timeout)
        return {
            "index": idx,
            "target": label,
            "alive": ok,
            "elapsed_ms": elapsed,
            "error": err,
            "peer_ip": peer_ip,
        }

    def run(self):
        total = len(self._targets)
        done = 0
        with ThreadPoolExecutor(max_workers=min(self._max_workers, max(1, total))) as executor:
            futures = [
                executor.submit(self._check_one, idx, raw)
                for idx, raw in enumerate(self._targets, start=1)
            ]
            for future in as_completed(futures):
                result = future.result()
                done += 1
                if self._emit_closed or result.get("alive"):
                    self.item_result.emit(result)
                self.progress.emit(done, total)
        self.finished.emit()

class ProxyPingBatchWorker(QObject):
    item_result = Signal(dict)
    progress = Signal(int, int)
    finished = Signal()

    def __init__(self, entries: list[str], default_protocol: str, max_workers: int = 16):
        super().__init__()
        self._entries = entries
        self._default_protocol = default_protocol
        self._max_workers = max(1, max_workers)

    def _probe_one(self, idx: int, raw: str) -> dict:
        proxy = parse_proxy(raw, default_protocol=self._default_protocol)
        if proxy is None:
            return {
                "index": idx,
                "label": raw,
                "alive": False,
                "elapsed_ms": 0.0,
                "error": "Invalid proxy format",
            }
        result = _probe_proxy(proxy)
        result["index"] = idx
        return result

    def run(self):
        total = len(self._entries)
        done = 0
        with ThreadPoolExecutor(max_workers=min(self._max_workers, max(1, total))) as executor:
            futures = [
                executor.submit(self._probe_one, idx, raw)
                for idx, raw in enumerate(self._entries, start=1)
            ]
            for future in as_completed(futures):
                done += 1
                self.item_result.emit(future.result())
                self.progress.emit(done, total)
        self.finished.emit()

def __getattr__(name: str):
    if name == "PingTab":
        from tabs.proxy import ProxyTab
        return ProxyTab
    if name == "CheckPortTab":
        from tabs.host import HostTab
        return HostTab
    if name == "PingModal":
        from tabs.modal import PingModal
        return PingModal
    raise AttributeError(name)


__all__ = [
    "CheckPortTab",
    "ParsedProxy",
    "PingModal",
    "PingTab",
    "PortBatchWorker",
    "ProxyPingBatchWorker",
    "parse_proxy",
]
