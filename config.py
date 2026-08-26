# standard imports
import re
import argparse


class Colors:
    CYAN: str = "\033[0;36m"
    RED: str = "\033[1;31m"
    YELLOW: str = "\033[0;33m"
    ORANGE: str = "\033[38;5;208m"
    GREEN: str = "\033[0;32m"
    NC: str = "\033[0m"


def cprint(msg: str, color: str = Colors.NC) -> None:
    print(f"{color}{msg}{Colors.NC}")


##################### CONFIG #####################

# Dictionary with supported HW models. Add new models here  k:v -> common name:[model names in serf for sled/host]
VALID_MODELS = {
    "YV2 TWINLAKE": ("YV2_TL", "TWINLAKES"),
    "YV2 NORTHDOME": ("YV2_ND", "NORTHDOME"),
    "YV3 DELTALAKE": ("YV3_DL", "DELTALAKE"),
}

# Dictionary with errors that are searched. Add new patterns here
ERROR_PATTERNS = {
    "powerup_prep": {
        "label": "Powerup Prep",
        "regex": re.compile(r"Powerup Prep", re.IGNORECASE),
        "severity": "critical",
    },
    "dimm": {
        "label": "DIMM Errors",
        "regex": re.compile(r"\bDIMM\b", re.IGNORECASE),
        "severity": "notice",
    },
    "pcie": {
        "label": "PCIe Errors",
        "regex": re.compile(r"PCIe", re.IGNORECASE),
        "severity": "warning",
    },
    "mcerr": {
        "label": "MCERR",
        "regex": re.compile(r"MCERR|MACHINE_CHK", re.IGNORECASE),
        "severity": "notice",
    },
    "caterr": {
        "label": "CATERR",
        "regex": re.compile(r"CATERR", re.IGNORECASE),
        "severity": "warning",
    },
    "ierr": {
        "label": "IERR",
        "regex": re.compile(r"\bIERR\b", re.IGNORECASE),
        "severity": "warning",
    },
}

# Colors for severity levels. Add new colors here
SEVERITY_COLORS: dict[str, str] = {
    "critical": Colors.RED,
    "warning": Colors.YELLOW,
    "notice": Colors.ORANGE,
}

# cri_sel timestamp ex: 2025 Dec  6 15:47:46 //  2026 Mar 17 15:22:15
cri_sel_time_pattern: re.Pattern = re.compile(
    r"^\s*(\d{4}\s+[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})"
)
cri_sel_time_format: str = "%Y %b %d %H:%M:%S"


##################


def create_cli_parser() -> argparse.ArgumentParser:
    model_list = "\n".join(f"        {m}" for m in sorted(set(VALID_MODELS.keys())))
    parser = argparse.ArgumentParser(
        prog="check_host",
        usage="check_host TARGET [OPTIONS]",
        description="Check logs and analyze for errors.",
        epilog=(
            f"{Colors.YELLOW}Caveats:\n    This script only supports:\n{model_list}{Colors.NC}\n"
            f"{Colors.GREEN}Examples:\n"
            f"    check_host.py sled1234frc2 --errors mcerr dimm\n"
            f"    check_host.py host1234frc2 --days 2 --all-hosts{Colors.NC}\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser._optionals.title = "Options"
    parser._positionals.title = None

    parser.add_argument(
        "target",
        help="hostname or sledname",
    )
    parser.add_argument(
        "--errors",
        nargs="+",
        metavar="",
        help=f"{Colors.YELLOW}Errors to search for:\n{', '.join(ERROR_PATTERNS.keys())}{Colors.NC}",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to keep in cri_sel filter (default: %(default)s)",
    )
    parser.add_argument(
        "--all-hosts",
        action="store_true",
        help=f"Skips host-position filter. {Colors.YELLOW}cri_sel and log-util results will be system-wide.{Colors.NC},
    )
    return parser

MAX_TERMINAL_LINES = 15

EXIT_INVALID_MODEL = 1
EXIT_USER_INT: int = 2
EXIT_SERF_ERROR: int = 3
EXIT_RUN_CMD_ERROR: int = 4
EXIT_SLED_LOG_FAIL: int = 5