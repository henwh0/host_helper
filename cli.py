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
from host_helper.system_calls import resolve_target_information


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
    sledname, sled_model_name, hostname, host_position = resolve_target_information(target, args)
    
    # Checks detected model against VALID_MODELS dict to ensure model is supported.
    model_name = validate_asset_model(sled_model_name)
    cprint(f"Detected model: {model_name}\n", Colors.GREEN)
    
    # Gathering sled data
    sled_analysis_start = perf_counter()
    dmesg_results, cri_sel_results, log_util_results, postcode_output = run_sled_analysis(sledname, args, host_position, hostname,)
    sled_analysis_end = perf_counter()

    # Print log results
    display_log_results(dmesg_results, cri_sel_results, log_util_results)
    
    if postcode_output:
        cprint(f"\n\n=== Postcodes for {hostname} ===", Colors.GREEN)
        print(postcode_output)
    cprint("\nRun complete!", Colors.GREEN)
    print("Performance stats:")
    print(f"Time to analyze logs & retrieve postcodes: {sled_analysis_end - sled_analysis_start:.2f} seconds")
    