# standard imports
import subprocess

# imports from local
from host_helper.config import Colors, cprint, EXIT_RUN_CMD_ERROR, EXIT_SLED_LOG_FAIL, EXIT_SERF_ERROR
from host_helper.parsing import parse_serf_output


def run_cmd(cmd: list[str]) -> str:
    """Run a subprocess command and return stripped stdout. Exits on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        cprint(f"cmd failed: {result.stderr}", Colors.RED)
        raise SystemExit(EXIT_RUN_CMD_ERROR)
    return result.stdout.strip()


#########n

CRI_SEL_DELIMITER: str = "=== CRI_SEL_START ==="
LOG_UTIL_DELIMITER: str = "=== LOG_UTIL_START ==="


def retrieve_sled_logs(sledname: str, host_position=None):
    """Get dmesg, cri_sel, and log-util in a single sush2 session."""
    combined_cmd = (
        f"dmesg; echo '{CRI_SEL_DELIMITER}'; cat /mnt/data/cri_sel"
    )

    if host_position is not None:
        combined_cmd = (
            f"{combined_cmd}; "
            f"echo '{LOG_UTIL_DELIMITER}'; "
            f"log-util slot{host_position} --print"
        )

    result = subprocess.run(
        ["sush2", sledname, combined_cmd],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        cprint(f"Failed to get logs from {sledname}: {result.stderr}", Colors.RED)
        raise SystemExit(EXIT_SLED_LOG_FAIL)

    parts = result.stdout.split(CRI_SEL_DELIMITER, 1)
    dmesg = parts[0].strip()
    remainder = parts[1] if len(parts) > 1 else ""

    # Split cri_sel from log-util output
    if LOG_UTIL_DELIMITER in remainder:
        cri_sel_part, log_util_part = remainder.split(LOG_UTIL_DELIMITER, 1)
        cri_sel = cri_sel_part.strip()
        log_util = log_util_part.strip()
    else:
        cri_sel = remainder.strip()
        log_util = ""

    return dmesg, cri_sel, log_util


#########


def run_hostory(sledname: str) -> None:
    """Run hostory for the sled."""
    subprocess.run(["hostory", "-sc", "--yard", sledname])

#########

def retrieve_host_postcodes(hostname: str) -> str:
    """Retrieves host postcodes for the given hostname."""
    return run_cmd(["hwc", "postcodes", hostname])

##
##########

def resolve_target_information(target, args):
    """Resolves target information.
    if hostname: resolves host model;sledname;rack_sub_position_slot
    if sledname: resolves sled model"""

    if target.startswith("sled"):
        info = parse_serf_output(run_cmd(["serf", "get", f"name={target}", "--fields=model"]))
        return target, info.get("model"), None, None

    # Target is a hostname — resolve to sled
    hostname = target
    need_position = not args.all_hosts
    fields = "parent_asset_tag,model"
    if need_position:
        fields += ",rack_sub_position_slot"

    host_info = parse_serf_output(
        run_cmd(["serf", "get", f"name={hostname}", f"--fields={fields}"])
    )
    sled_asset_tag = host_info.get("parent_asset_tag")
    if not sled_asset_tag:
        cprint(f"No parent asset tag found for {hostname}.", Colors.RED)
        raise SystemExit(EXIT_SERF_ERROR)

    sled_model_name = host_info.get("model")

    host_position = None
    if need_position:
        raw_pos = host_info.get("rack_sub_position_slot")
        if raw_pos:
            try:
                host_position = int(raw_pos)
            except ValueError:
                cprint(f"Could not parse host position '{raw_pos}' from {hostname}", Colors.RED)

    # Resolve sledname from parent asset tag
    sled_info = parse_serf_output(
        run_cmd(["serf", "get", f"asset_tag={sled_asset_tag}", "--fields=name"])
    )
    sledname = sled_info.get("name", sled_asset_tag)

    return sledname, sled_model_name, hostname, host_position
