from concurrent.futures import ThreadPoolExecutor
# import from local
from host_helper.config import EXIT_SERF_ERROR, EXIT_INVALID_MODEL, EXIT_SLED_LOG_FAIL, Colors, cprint, VALID_MODELS
from host_helper.log_tools import (
    scan_sled_logs_for_errors,
    filter_cri_sel_by_age,
    filter_cri_sel_by_host_position,
)
from host_helper.system_calls import run_hostory, retrieve_sled_logs, retrieve_host_postcodes


def run_sled_analysis(sledname, args, host_position=None, hostname=None, slots=None):
    """Run hostory, retrieve sled logs, apply filters and analyze for errors"""

    cprint(f"=== Hostory cmd for {sledname} ===", Colors.CYAN)
    #####
    with ThreadPoolExecutor(max_workers=3) as executor:
        hostory_future = executor.submit(run_hostory, sledname)
        logs_future = executor.submit(retrieve_sled_logs, sledname, host_position, slots)
        postcode_future = executor.submit(retrieve_host_postcodes, hostname) if hostname else None
        try:
            ##
            sled_dmesg, sled_cri_sel, sled_log_util = logs_future.result()
            ##
            hostory_future.result()

            postcode_output = postcode_future.result() if postcode_future else None
        except Exception as e:
            cprint(f"Log collection failed: {e}", Colors.RED)
            raise SystemExit(EXIT_SLED_LOG_FAIL)

    cprint(f"\n=== Processing logs for {sledname} ===", Colors.CYAN)

    if sled_dmesg is None or sled_cri_sel is None:
        cprint("Failed to retrieve sled logs.", Colors.RED)
        raise SystemExit(EXIT_SLED_LOG_FAIL)

    sled_cri_sel = filter_cri_sel_by_age(sled_cri_sel, args.days)
    cprint(f"    (cri_sel filtered to: {args.days} days)", Colors.GREEN)

    if host_position is not None:
        sled_cri_sel = filter_cri_sel_by_host_position(sled_cri_sel, host_position)
        cprint(f"    (cri_sel filtered to host position: FRU:{host_position})",Colors.GREEN)

        if sled_log_util:
            cprint(f"    (log-util collected for slot{host_position})", Colors.GREEN)

    if args.errors:
        errors = ", ".join(err.upper() for err in args.errors)
        cprint(f"    (filtering for errors: {errors})", Colors.GREEN)
    else:
        cprint(f"    (searching for all error patterns)", Colors.GREEN)


    # Apply filters before regex scan
    return scan_sled_logs_for_errors(sled_dmesg, sled_cri_sel, sled_log_util, postcode_output, args.errors)


#########


def validate_asset_model(model) -> str:
    """Validate the detected asset model against the VALID_MODELS dict"""

    if not model:
        cprint("No model detected from serf.", Colors.RED)
        raise SystemExit(EXIT_SERF_ERROR)

    for common_name, aliases in VALID_MODELS.items():
        if model.startswith(aliases):
            return common_name

    cprint(f"Model '{model}' is not supported.", Colors.RED)
    raise SystemExit(EXIT_INVALID_MODEL)
