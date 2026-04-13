import sys, re, subprocess

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
    }
}


SEVERITY_COLORS = {
    "critical": RED,
    "warning": YELLOW,
    "info": CYAN,
}


# Helper functions
def run_cmd(cmd, shell=True):
    """Run a shell command and return stripped stdout."""
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
        capture_output=True, text=True,
    ).stdout


def run_sled_cri_sel(sledname):
    return subprocess.run(
        ["sush2", sledname, "cat /mnt/data/cri_sel | tail -n 30"],
        capture_output=True, text=True,
    ).stdout


# Log analysis
def analyze_log(log_text):
    """Scan log_text against every ERROR_PATTERN. Returns dict of results."""
    results = {}
    for key, pattern in ERROR_PATTERNS.items():
        matches = [
            line for line in log_text.splitlines()
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
def check_sled(sledname):
    """Run hostory, pull dmesg/cri_sel, analyze, and pastry the dmesg log."""
    print(f"{CYAN}===Hostory command for {sledname}==={NC}")
    run_hostory(sledname)

    print(f"\n{CYAN}===Getting dmesg for {sledname}==={NC}")
    sled_dmesg = run_sled_dmesg(sledname)

    print(f"\n{CYAN}===Analyzing Logs==={NC}")
    results = analyze_log(sled_dmesg)
    print_analysis(results)

    print(f"\n{YELLOW}===Full dmesg output:==={NC}")
    pastry_output = run_pastry(sled_dmesg)
    print(pastry_output)

    print(f"\n{CYAN}===Retrieving sled cri_sel logs==={NC}")
    sled_cri_sel = run_sled_cri_sel(sledname)
    print(f"\n{sled_cri_sel}")


def host_postcodes(hostname):
    """Prompt the user, then gather postcodes for a hostname."""
    answer = input(f"{YELLOW}Do you want to gather host postcodes? [y/n]: {NC}").strip().lower()
    if answer == "y":
        print(f"\n{GREEN}===Postcodes for {hostname}==={NC}")
        subprocess.run(["hwc", "postcodes", hostname], text=True)
        print(f"\n{GREEN}Run Complete!{NC}")
    else:
        print(f"\n{GREEN}Run Complete Without POST codes!{NC}")




def usage():
    model_list = "\n".join(sorted(set(VALID_MODELS.values())))
    print(f"{CYAN}Usage: 'python3 checkhost.py' <sledname> OR <hostname>{NC}")
    print(f"{CYAN}Options: [-h][--help] shows this help page, then exits{NC}")
    print(f"\n{YELLOW}Caveats: This script currently only runs on the following server types:{NC}")
    print(f"{YELLOW}{model_list}{NC}")


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
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    arg = sys.argv[1]

    if arg in ("-h", "--help"):
        usage()
        sys.exit(0)

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
    check_sled(sledname)

    # If a hostname was given, ask if you want postcodes, else exit
    if hostname:
        host_postcodes(hostname)
    else:
        print(f"\n{GREEN}Run complete!{NC}")


if __name__ == "__main__":
    main()
