from macropulse.api.main import health

def main() -> None:
    result = health()
    if result["status"] != "ok":
        raise SystemExit("smoke test failed")
    print("MacroPulse starter smoke test passed")

if __name__ == "__main__":
    main()
