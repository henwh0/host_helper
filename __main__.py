# imports from local
from host_helper.cli import main
from host_helper.config import EXIT_USER_INT, Colors, cprint

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cprint(f"Exiting: user interrupt", Colors.YELLOW)
        raise SystemExit(EXIT_USER_INT)
