custom_to_csv.py# cli/custom_to_csv.py
import argparse
import csv
from typing import List, Optional

from columnar.reader import read_as_rows


def main():
Add custom_to_csv CLI tool        description="Convert custom columnar file to CSV"
    )
    parser.add_argument("input_file", help="Input custom file path")
    parser.add_argument("output_csv", help="Output CSV file path")
    parser.add_argument(
        "--columns",
        help="Comma-separated list of columns to read (for column pruning)",
        default=None,
    )

    args = parser.parse_args()
    cols: Optional[List[str]] = None
    if args.columns:
        cols = [c.strip() for c in args.columns.split(",") if c.strip()]

    rows = read_as_rows(args.input_file, columns=cols)
    if not rows:
        with open(args.output_csv, "w", newline="", encoding="utf-8") as f:
            pass
        return

    fieldnames = list(rows[0].keys())
    with open(args.output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


if __name__ == "__main__":
    main()
