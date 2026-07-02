from __future__ import annotations

from copy import deepcopy
from typing import Any


PLATFORM_KEYS = ("tiktok", "google", "facebook", "instagram")
PLATFORM_LABELS = {
    "tiktok": "TikTok",
    "google": "Google",
    "facebook": "Facebook",
    "instagram": "Instagram",
}

HOSTING_MARKERS = (
    "amazon",
    "aws",
    "azure",
    "microsoft",
    "google cloud",
    "digitalocean",
    "hetzner",
    "ovh",
    "oracle",
    "vultr",
    "linode",
    "akamai",
    "alibaba",
    "tencent",
    "contabo",
    "leaseweb",
    "choopa",
    "m247",
    "colo",
    "colocation",
    "data center",
    "datacenter",
    "hosting",
    "server",
    "cloud",
    "vps",
)

RESIDENTIAL_MARKERS = (
    "comcast",
    "xfinity",
    "verizon",
    "at&t",
    "spectrum",
    "charter",
    "cox",
    "centurylink",
    "frontier",
    "rogers",
    "bell",
    "telus",
    "bt",
    "virgin media",
    "deutsche telekom",
    "vodafone",
    "orange",
    "telefonica",
    "telstra",
    "optus",
    "singtel",
    "starhub",
    "viettel",
    "vnpt",
    "fpt",
)

PLATFORM_SENSITIVITY = {
    "google": 0.85,
    "facebook": 1.0,
    "instagram": 1.08,
    "tiktok": 1.12,
}


def clamp_score(value: float | int | None) -> int:
    if value is None:
        return 0
    return max(0, min(100, int(round(float(value)))))


def score_latency(elapsed_ms: float | int | None) -> int:
    try:
        elapsed = float(elapsed_ms or 0)
    except (TypeError, ValueError):
        elapsed = 0

    if elapsed <= 0:
        return 35
    if elapsed <= 120:
        return 100
    if elapsed <= 250:
        return 92
    if elapsed <= 500:
        return 82
    if elapsed <= 900:
        return 70
    if elapsed <= 1500:
        return 56
    if elapsed <= 2500:
        return 40
    return 24


def _network_text(result: dict[str, Any]) -> str:
    parts = [
        result.get("asn", ""),
        result.get("isp", ""),
        result.get("org", ""),
    ]
    return " ".join(str(part).lower() for part in parts if part)


def classify_network(result: dict[str, Any]) -> tuple[str, int, list[str]]:
    text = _network_text(result)
    flags: list[str] = []
    if any(marker in text for marker in HOSTING_MARKERS):
        flags.append("datacenter_or_hosting_signal")
        return "Datacenter", 55, flags
    if any(marker in text for marker in RESIDENTIAL_MARKERS):
        return "Residential-like", 92, flags
    if not text:
        flags.append("missing_asn_isp")
        return "Unknown", 70, flags
    return "Unknown", 76, flags


def _platform_probe_score(check: dict[str, Any] | None) -> int | None:
    if not check:
        return None

    verdict = str(check.get("verdict", "")).lower()
    try:
        status = int(check.get("status_code") or 0)
    except (TypeError, ValueError):
        status = 0

    if verdict == "ok":
        return 96 if status in (200, 204) else 88
    if verdict == "redirect":
        return 82
    if verdict == "challenge":
        return 58
    if verdict == "limited":
        return 32
    if verdict == "blocked":
        return 15
    if verdict == "error":
        return 24
    if 200 <= status < 300:
        return 88
    if 300 <= status < 400:
        return 76
    if status in (401, 407):
        return 28
    if status in (403, 451):
        return 12
    if status == 429:
        return 22
    return 35 if status else 24


def _estimate_platform_score(
    platform: str,
    latency_score: int,
    network_score: int,
    health_score: int,
    result: dict[str, Any],
) -> int:
    sensitivity = PLATFORM_SENSITIVITY.get(platform, 1.0)
    score = (latency_score * 0.42) + (network_score * 0.38) + (health_score * 0.20)

    ip_type = str(result.get("ip_type", "Unknown"))
    if ip_type == "Datacenter":
        score -= 10 * sensitivity
    elif ip_type == "Residential-like":
        score += 4

    if not result.get("country_code") and not result.get("country"):
        score -= 5
    if platform in ("instagram", "tiktok") and latency_score < 55:
        score -= 8
    return clamp_score(score)


def _platform_score_from_probe(
    platform: str,
    probe_score: int,
    latency_score: int,
    network_score: int,
    result: dict[str, Any],
) -> int:
    sensitivity = PLATFORM_SENSITIVITY.get(platform, 1.0)
    score = (probe_score * 0.58) + (latency_score * 0.22) + (network_score * 0.20)
    if result.get("ip_type") == "Datacenter":
        score -= 6 * sensitivity
    if platform in ("instagram", "tiktok") and latency_score < 55:
        score -= 6
    return clamp_score(score)


def _extract_proxy_type(result: dict[str, Any]) -> str:
    label = str(result.get("label") or result.get("source") or "").strip()
    if not label:
        return "-"
    first = label.split(maxsplit=1)[0].upper()
    if first in {"HTTP", "HTTPS", "SOCKS4", "SOCKS5", "SOCKS5H"}:
        return "SOCKS5" if first == "SOCKS5H" else first
    if "://" in label:
        return label.split("://", 1)[0].upper().replace("SOCKS5H", "SOCKS5")
    return "-"


def enrich_proxy_result(result: dict[str, Any]) -> dict[str, Any]:
    enriched = deepcopy(result)
    alive = enriched.get("alive")
    enriched["proxy_type"] = enriched.get("proxy_type") or _extract_proxy_type(enriched)
    enriched["tcp_ok"] = True if alive is True else False if alive is False else None
    enriched["udp_ok"] = None

    if alive is None:
        enriched.setdefault("platform_scores", {})
        enriched.setdefault("avg_score", None)
        enriched.setdefault("quality", "Pending")
        enriched.setdefault("risk_flags", [])
        return enriched

    if alive is not True:
        enriched["ip_type"] = "Unknown"
        enriched["latency_score"] = 0
        enriched["network_score"] = 0
        enriched["platform_scores"] = {key: 0 for key in PLATFORM_KEYS}
        enriched["avg_score"] = 0
        enriched["quality"] = "Dead"
        enriched["risk_flags"] = ["dead_or_unreachable"]
        return enriched

    latency_score = score_latency(enriched.get("elapsed_ms"))
    ip_type, network_score, flags = classify_network(enriched)
    enriched["ip_type"] = ip_type
    enriched["latency_score"] = latency_score
    enriched["network_score"] = network_score

    risk_flags = list(flags)
    elapsed = float(enriched.get("elapsed_ms") or 0)
    if elapsed > 1500:
        risk_flags.append("very_slow")
    elif elapsed > 900:
        risk_flags.append("slow")
    expected_ip = str(enriched.get("expected_ip") or "").strip()
    response_ip = str(enriched.get("response_ip") or "").strip()
    if expected_ip and response_ip and expected_ip != response_ip:
        risk_flags.append("public_ip_mismatch")

    platform_checks = enriched.get("platform_checks") or {}
    platform_scores: dict[str, int] = {}
    for key in PLATFORM_KEYS:
        probe_score = _platform_probe_score(platform_checks.get(key))
        if probe_score is None:
            platform_scores[key] = _estimate_platform_score(
                key, latency_score, network_score, 100, enriched
            )
        else:
            platform_scores[key] = _platform_score_from_probe(
                key, probe_score, latency_score, network_score, enriched
            )

        verdict = str((platform_checks.get(key) or {}).get("verdict", "")).lower()
        if verdict in {"blocked", "limited", "challenge"}:
            risk_flags.append(f"{key}_{verdict}")

    avg_score = clamp_score(sum(platform_scores.values()) / max(1, len(platform_scores)))
    if avg_score >= 80:
        quality = "Good"
    elif avg_score >= 60:
        quality = "Fair"
    elif avg_score >= 35:
        quality = "Weak"
    else:
        quality = "Bad"

    enriched["platform_scores"] = platform_scores
    enriched["avg_score"] = avg_score
    enriched["quality"] = quality
    enriched["risk_flags"] = risk_flags
    return enriched


def score_text(score: int | float | None) -> str:
    if score is None:
        return "-"
    return str(clamp_score(score))


def proxy_status_text(value: bool | None, pending: str = "WAIT") -> str:
    if value is True:
        return "PASS"
    if value is False:
        return "FAIL"
    return pending


def score_tone(score: int | float | None) -> str:
    if score is None:
        return "muted"
    score_value = clamp_score(score)
    if score_value >= 80:
        return "good"
    if score_value >= 60:
        return "warn"
    return "bad"


def proxy_table_fields(result: dict[str, Any]) -> dict[str, str]:
    scores = result.get("platform_scores") or {}
    elapsed = result.get("elapsed_ms", 0.0) or 0.0
    ms = f"{elapsed:.0f}" if elapsed else "-"
    risk_flags = result.get("risk_flags") or []
    return {
        "index": f"{int(result.get('index', 0) or 0):02d}",
        "proxy": str(result.get("source") or result.get("label") or "-"),
        "type": str(result.get("proxy_type") or "-"),
        "ip_public": str(result.get("response_ip") or "-"),
        "location": _location_text(result),
        "ms": ms,
        "tcp": proxy_status_text(result.get("tcp_ok")),
        "udp": "N/A" if result.get("udp_ok") is None else proxy_status_text(result.get("udp_ok")),
        "avg": score_text(result.get("avg_score")),
        "tiktok": score_text(scores.get("tiktok")),
        "google": score_text(scores.get("google")),
        "facebook": score_text(scores.get("facebook")),
        "instagram": score_text(scores.get("instagram")),
        "quality": str(result.get("quality") or "-"),
        "risk": ", ".join(risk_flags) if risk_flags else "-",
    }


def format_proxy_detail(result: dict[str, Any]) -> str:
    fields = proxy_table_fields(result)
    lines = [
        f"Proxy: {fields['proxy']}",
        f"Type: {fields['type']}",
        f"Status: TCP {fields['tcp']} | UDP {fields['udp']}",
        f"Public IP: {fields['ip_public']}",
        f"Expected public IP: {result.get('expected_ip') or '-'}",
        f"Latency: {fields['ms']} ms",
        f"Quality: {fields['quality']} | AVG {fields['avg']}/100",
        f"IP type: {result.get('ip_type') or '-'}",
        f"Location: {_location_text(result)}",
        f"ASN: {result.get('asn') or '-'}",
        f"ISP/Org: {result.get('isp') or result.get('org') or '-'}",
        "",
        "Platform scores:",
    ]
    for key in PLATFORM_KEYS:
        label = PLATFORM_LABELS[key]
        score = fields[key]
        check = (result.get("platform_checks") or {}).get(key) or {}
        verdict = check.get("verdict") or ("estimated" if score != "-" else "-")
        status = check.get("status_code") or "-"
        lines.append(f"- {label}: {score}/100 ({verdict}, HTTP {status})")

    if result.get("alive") is None:
        info = result.get("info")
    else:
        info = result.get("info") if result.get("alive") else result.get("error")
    lines.extend(
        [
            "",
            f"Info: {info or '-'}",
            f"Risk flags: {fields['risk']}",
            "",
            "Note: platform scores are internal estimates, not official trust scores.",
        ]
    )
    return "\n".join(lines)


def _location_text(result: dict[str, Any]) -> str:
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


def export_proxy_row(result: dict[str, Any]) -> dict[str, str]:
    fields = proxy_table_fields(result)
    return {
        "#": fields["index"],
        "proxy": fields["proxy"],
        "source": str(result.get("source") or ""),
        "type": fields["type"],
        "public_ip": fields["ip_public"],
        "expected_ip": str(result.get("expected_ip") or ""),
        "location": fields["location"],
        "ms": fields["ms"],
        "tcp": fields["tcp"],
        "udp": fields["udp"],
        "avg": fields["avg"],
        "tiktok": fields["tiktok"],
        "google": fields["google"],
        "facebook": fields["facebook"],
        "instagram": fields["instagram"],
        "quality": fields["quality"],
        "ip_type": str(result.get("ip_type") or ""),
        "country": str(result.get("country") or ""),
        "country_code": str(result.get("country_code") or ""),
        "region": str(result.get("region") or ""),
        "city": str(result.get("city") or ""),
        "asn": str(result.get("asn") or ""),
        "isp": str(result.get("isp") or ""),
        "risk": fields["risk"],
        "info": str(
            (result.get("info") if result.get("alive") is not False else result.get("error"))
            or ""
        ),
    }


def format_proxy_clipboard_line(result: dict[str, Any]) -> str:
    row = export_proxy_row(result)
    return "\t".join(
        row[key]
        for key in (
            "#",
            "proxy",
            "type",
            "public_ip",
            "location",
            "ms",
            "tcp",
            "avg",
            "quality",
            "risk",
        )
    )
