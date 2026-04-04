"""No-op worker used for Render debug deployments."""
import time

def main() -> None:
    print("[noop_worker] starting")
    while True:
        time.sleep(30)

if __name__ == "__main__":
    main()
