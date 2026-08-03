from time import perf_counter

# imports from local
from host_helper.config import (
    Colors,
    cprint,
    SEVERITY_COLORS,
    MAX_TERMINAL_LINES,
    create_cli_parser,
)
from host_helper.core import run_sled_analysis, validate_asset_model
from host_helper.system_calls import show_host_postcodes, resolve_target_information


def display_log_results(dmesg_results, cri_sel_results, log_util_results=None):
    
    """Print formatted results for each log source."""
    cprint("\n\n=== sled_dmesg ===\n", Colors.CYAN)
    display_error_results(dmesg_results)

    cprint("\n\n=== sled_cri_sel ===\n", Colors.CYAN)
    display_error_results(cri_sel_results)

    if log_util_results:
        cprint("\n\n=== log-util ===\n", Colors.CYAN)
        display_error_results(log_util_results)


#########


def display_error_results(results):
    """Print analysis results with severity coloring."""
    any_matches = False

    for data in results.values():
        color = SEVERITY_COLORS.get(data["severity"], Colors.NC)
        if not data["matches"]:
            continue

        any_matches = True
        total_matches = len(data["matches"])
        print(f"\n{color}=== Found {data['label']} ==={Colors.NC}")

        matches = data["matches"]
        if total_matches > MAX_TERMINAL_LINES:
            print(
                f"{color}...({total_matches - MAX_TERMINAL_LINES} earlier lines omitted)...{Colors.NC}"
            )
            matches = matches[-MAX_TERMINAL_LINES:]

        for line in matches:
            print(f"{color}{line}{Colors.NC}")

    if not any_matches:
        cprint("No matches found..", Colors.GREEN)


#########


def main() -> None:
    """CLI entry point."""
    parser = create_cli_parser()
    args = parser.parse_args()

    if args.errors:
        args.errors = [error.lower() for error in args.errors]
    target: str = args.target

    # Resolve target information
    resolve_target_start = perf_counter()
    sledname, sled_model_name, hostname, host_position = resolve_target_information(target, args)
    resolve_target_end = perf_counter()
    # Checks detected model against VALID_MODELS dict to ensure model is supported.
    validate_start = perf_counter()
    model_name = validate_asset_model(sled_model_name)
    cprint(f"Detected model: {model_name}\n", Colors.GREEN)
    validate_end = perf_counter()
    # Gathering log results
    sled_analysis_start = perf_counter()
    dmesg_results, cri_sel_results, log_util_results = run_sled_analysis(sledname, args, host_position)
    sled_analysis_end = perf_counter()
    # Print log results
    display_start = perf_counter()
    display_log_results(dmesg_results, cri_sel_results, log_util_results)
    display_end = perf_counter()
    if hostname:
        postcode_start = perf_counter()
        cprint(f"\n\n=== Postcodes for {hostname} ===", Colors.GREEN)
        show_host_postcodes(hostname)
        postcode_end = perf_counter()
    cprint("\nRun complete!", Colors.GREEN)
    print("Performance stats:")
    print(f"Time to resolve target information: {resolve_target_end - resolve_target_start:.2f} seconds")
    print(f"Time to validate model: {validate_end - validate_start:.2f} seconds")
    print(f"Time to analyze logs: {sled_analysis_end - sled_analysis_start:.2f} seconds")
    print(f"Time to display logs: {display_end - display_start:.2f} seconds")
    if hostname:
        print(f"Time to retrieve postcodes: {postcode_end - postcode_start:.2f} seconds")
    