# standard imports
import re
from datetime import datetime, timedelta

# imports from local
from host_helper.config import cri_sel_time_format, cri_sel_time_pattern, ERROR_PATTERNS


def scan_log_for_errors(log_text, selected_errors = None) -> dict[str, dict]:
    """Scan log_text against every ERROR_PATTERN. Returns dict of results."""

    if not log_text:
        return {
            key: {"label": ERROR_PATTERNS[key]["label"], "severity": ERROR_PATTERNS[key]["severity"], "matches": []}
            for key in (selected_errors or list(ERROR_PATTERNS))
            if key in ERROR_PATTERNS
        }

    errors_to_search = selected_errors or list(ERROR_PATTERNS)

    results: dict[str, dict] = {}

    for key in errors_to_search:
        if key not in ERROR_PATTERNS:
            continue
        pattern_data = ERROR_PATTERNS[key]
        results[key] = {
            "label": pattern_data["label"],
            "severity": pattern_data["severity"],
            "matches": [],
        }

    combined_regex = re.compile(
        "|".join(
            f"(?P<{key}>{ERROR_PATTERNS[key]['regex'].pattern})"
            for key in errors_to_search
            if key in ERROR_PATTERNS
        ),
        re.IGNORECASE,
    )

    lines = log_text.splitlines() if isinstance(log_text, str) else log_text

    for line in lines:
        match = combined_regex.search(line)
        if match:
            matched_key = match.lastgroup
            results[matched_key]["matches"].append(line)

    return results


#########


def filter_cri_sel_by_age(log_text: str, days: int = 30) -> str:
    """Filter cri_sel to only include logs newer than N days.
    Lines without timestamp are saved to preserve data"""
    cutoff = datetime.now() - timedelta(days=days)
    filtered_lines: list[str] = []

    for line in log_text.splitlines():
        m = cri_sel_time_pattern.match(line)
        if not m:
            filtered_lines.append(line)
            continue

        try:
            log_time = datetime.strptime(m.group(1), cri_sel_time_format)
            if log_time >= cutoff:
                filtered_lines.append(line)
        except ValueError:
            filtered_lines.append(line)

    return "\n".join(filtered_lines)


def filter_cri_sel_by_host_position(log_text: str, host_position: int) -> str:
    """Filter cri_sel lines to only those matching FRU:<host_position>."""
    pattern = f"FRU:{int(host_position)}"
    return "\n".join(line for line in log_text.splitlines() if pattern in line)

###########

def scan_sled_logs_for_errors(
    dmesg,
    cri_sel,
    log_util,
    selected_errors = None,
):
    """Analyze all logs. Returns None for log_util if input is empty."""
    dmesg_results = scan_log_for_errors(dmesg, selected_errors=selected_errors)
    cri_sel_results = scan_log_for_errors(cri_sel, selected_errors=selected_errors)
    log_util_results = scan_log_for_errors(log_util, selected_errors=selected_errors) if log_util else None
    return dmesg_results, cri_sel_results, log_util_results
