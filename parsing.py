def parse_serf_output(text: str) -> dict[str, str]:
    """Parse key=value output from serf into a dictionary."""
    result: dict[str, str] = {}

    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result