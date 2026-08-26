def parse_serf_output(text: str) -> list[dict[str, str]]:
    """Parse key=value output from serf into a dictionary."""
    result: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            if current:
                result.append(current)
                current = {}
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            current[key.strip()] = value.strip()
    if current:
        result.append(current)
    return result