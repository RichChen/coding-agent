def main():
    with open("input.csv", encoding="utf-8") as f:
        rows = f.read().splitlines()[1:]
    with open("summary.md", "w", encoding="utf-8") as f:
        f.write("# Summary\n")
        f.write(f"Rows: {len(rows)}\n")


if __name__ == "__main__":
    main()
