from time import perf_counter
# imports from local
from host_helper.cli import main
from host_helper.config import EXIT_USER_INT, Colors, cprint

if __name__ == "__main__":
    start_time = perf_counter()
    try:
        main()
    except KeyboardInterrupt:
        cprint(f"Exiting: user interrupt", Colors.YELLOW)
        raise SystemExit(EXIT_USER_INT)
    finally:
        end_time = perf_counter()
        print(f"Total runtime: {end_time - start_time:.2f} seconds")
