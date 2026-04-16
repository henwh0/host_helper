import re, subprocess, argparse
from datetime import datetime, timedelta

# ANSI color codes
CYAN = "\033[0;36m"
RED = "\033[1;31m"
YELLOW = "\033[0;33m"
GREEN = "\033[0;32m"
NC = "\033[0m"

# Dictionary with supported HW models. Add new models here
VALID_MODELS = {
    "YV2_TL": "YV2 TWINLAKE",
    "TWINLAKES": "YV2 TWINLAKE",
    "YV2_ND": "YV2 NORTH_DOME",
    "NORTHDOME": "YV2 NORTH_DOME",
    "YV3_DL": "YV3 DELTALAKE",
    "DELTALAKE": "YV3 DELTALAKE",
}


# Dictionary with errors that are searched. Add new patterns here
ERROR_PATTERNS = {
    "powerup_prep": {
        "label": "Powerup Prep",
        "regex": r"Powerup Prep",
        "severity": "critical",
    },
    "dimm": {
        "label": "DIMM Errors",
        "regex": r"DIMM [A-Z][0-9]",
        "severity": "warning",
    },
    "pcie": {
        "label": "PCIe Errors",
        "regex": r"PCIe",
        "severity": "warning",
    },
    "mcerr": {
        "label": "MCERR",
        "regex": r"MCERR|MACHINE_CHK",
        "severity": "critical",
    },
    "caterr": {
        "label": "CATERR",
        "regex": r"CATERR",
        "severity": "critical",
    },
    "ierr": {
        "label": "IERR",
        "regex": r"\bIERR\b",
        "severity": "critical",
    },
}


SEVERITY_COLORS = {
    "critical": RED,
    "warning": YELLOW,
    "info": CYAN,
}



# Filter cri_sel for last 30 days of logs
# cri_sel timestamp ex: 2025 Dec  6 15:47:46 //  2026 Mar 17 15:22:15 SEE THAT THERE IS AN EXTRA BLANK SPACE IN BETWEEN MONTH AND DAY IF DAY ONLY HAS ONE NUMBER
cri_sel_time_pattern = re.compile(r"^\s*(\d{4}\s+[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})")
cri_sel_time_format = "%Y %b %d %H:%M:%S"


def filter_cri_sel_by_date(log_text: str, days: int = 30) -> str:
    """Filter cri_sel to only print logs that are N days old"""
    cutoff = datetime.now() - timedelta(days=days)
    filtered_lines = []

    for line in log_text.splitlines():
        m = cri_sel_time_pattern.match(line)
        if m:
            try:
                log_time = datetime.strptime(m.group(1), cri_sel_time_format)
                if log_time >= cutoff:
                    filtered_lines.append(line)
            except ValueError:
                filtered_lines.append(line)

    return "\n".join(filtered_lines)


# Helper functions
def run_cmd(cmd, shell=True):
    """Run a shell command and return stdout."""
    result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
    return result.stdout.strip()


def run_pastry(text: str) -> str:
    """Pipe text into pastry."""
    process = subprocess.Popen(
        ["pastry"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = process.communicate(input=text)
    if process.returncode != 0:
        print(f"{RED}Pastry failed:{NC}\n{err}")
    return out.strip()


def run_hostory(sledname):
    """Run hostory for the sled."""
    subprocess.run(["hostory", "-sc", "--yard", sledname])


def run_sled_dmesg(sledname):
    return subprocess.run(
        ["sush2", sledname, "dmesg"],
        capture_output=True,
        text=True,
    ).stdout


def run_sled_cri_sel(sledname):
    return subprocess.run(
        ["sush2", sledname, "cat /mnt/data/cri_sel"],
        capture_output=True,
        text=True,
    ).stdout


# Log analysis
def analyze_log(log_text):
    """Scan log_text against every ERROR_PATTERN. Returns dict of results."""
    results = {}
    for key, pattern in ERROR_PATTERNS.items():
        matches = [
            line
            for line in log_text.splitlines()
            if re.search(pattern["regex"], line, re.IGNORECASE)
        ]
        results[key] = {
            "label": pattern["label"],
            "severity": pattern["severity"],
            "matches": matches,
        }
    return results


def print_analysis(results):
    """Print analysis results with severity based coloring."""
    for key, data in results.items():
        color = SEVERITY_COLORS.get(data["severity"], NC)
        if data["matches"]:
            print(f"\n{color}===Found {data['label']}==={NC}")
            for line in data["matches"]:
                print(f"{color}{line}{NC}")
        else:
            print(f"\n{GREEN}===No {data['label']} found==={NC}")


# Core functions
def check_sled(sledname, days):
    """Run hostory, pull dmesg/cri_sel, analyze, and pastry the dmesg log."""
    print(f"{CYAN}===Hostory command for {sledname}==={NC}")
    run_hostory(sledname)

    print(f"\n{CYAN}===Getting dmesg for {sledname}==={NC}")
    sled_dmesg = run_sled_dmesg(sledname)

    print(f"\n{CYAN}===Getting cri_sel for {sledname}==={NC}")
    raw_sled_cri_sel = run_sled_cri_sel(sledname)

    # Filter cri_sel to the last N days
    sled_cri_sel = filter_cri_sel_by_date(raw_sled_cri_sel, days=days)
    print(f"{GREEN} (Filtered to {days} days){NC}")

    print(f"\n{CYAN}===Analyzing Logs==={NC}\n")
    dmesg_results = analyze_log(sled_dmesg)
    cri_sel_results = analyze_log(sled_cri_sel)
    print(f"\n\n{CYAN}===sled dmesg==={NC}\n")
    print_analysis(dmesg_results)
    print(f"\n\n{CYAN}===sled cri_sel==={NC}\n")
    print_analysis(cri_sel_results)

    print(f"\n{GREEN}===Full dmesg output:==={NC}")
    pastry_output = run_pastry(sled_dmesg)
    print(pastry_output)


def host_postcodes(hostname):
    """Prompt the user, then gather postcodes for a hostname."""
    answer = (
        input(f"{YELLOW}Do you want to gather host postcodes? [y/n]: {NC}")
        .strip()
        .lower()
    )
    if answer == "y":
        print(f"\n{GREEN}===Postcodes for {hostname}==={NC}")
        subprocess.run(["hwc", "postcodes", hostname], text=True)
        print(f"\n{GREEN}Run Complete!{NC}")
    else:
        print(f"\n{GREEN}Run Complete Without POST codes!{NC}")


def resolve_sled(hostname):
    """Use serf to turn a hostname into its parent sled name."""
    raw_asset = run_cmd(f'serf get name="{hostname}" --fields=parent_asset_tag')
    sled_asset_tag = raw_asset.split()[2] if len(raw_asset.split()) > 2 else raw_asset
    raw_sled = run_cmd(f'serf get asset_tag="{sled_asset_tag}" --fields=name')
    return raw_sled.split()[2] if len(raw_sled.split()) > 2 else raw_sled


def validate_model(name):
    """Check that the asset model is supported; exit if not."""
    raw_model = run_cmd(f'serf get name="{name}" --fields=model')
    model_name = raw_model.split()[2] if len(raw_model.split()) > 2 else raw_model

    for key, friendly_name in VALID_MODELS.items():
        if model_name.startswith(key):
            print(f"{GREEN}Detected model: {friendly_name}{NC}\n")
            return
    print(f"{RED}Type: {model_name} is not applicable.{NC}")
    print(f"Try: -h/--help to see applicable HW types.")
    raise SystemExit(1)

##################################################################
def build_parser():
    model_list = "\n".join(sorted(set(VALID_MODELS.values())))
    parser = argparse.ArgumentParser(
        description="Check host/sled logs and analyze for errors.",
        epilog=f"Caveats:\nThis script only supports:\n{model_list}",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "target",
        help="hostname or sledname",
        
    )
    parser.add_argument(
        "--skip-postcodes",
        action="store_true",
        help="Do not prompt for postcodes",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to keep in cri_sel filter (default: %(default) s)",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    
    arg = args.target
    
    # Validate model first
    validate_model(arg)

    # Resolve sled name
    if arg.startswith("sled"):
        sledname = arg
        hostname = None
    else:
        hostname = arg
        sledname = resolve_sled(hostname)

    # Run sled checks
    check_sled(sledname, days=args.days)

    # If a hostname was given, ask if you want postcodes, else exit
    if hostname:
        if not args.skip_postcodes:
            host_postcodes(hostname)
    else:
        print(f"\n{GREEN}Run complete!{NC}")


if __name__ == "__main__":
    main()