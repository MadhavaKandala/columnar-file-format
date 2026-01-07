# cli/csv_to_custom.py
import argparse
import json
from typing import List, Tuple

from columnar.writer import write_from_csv


def parse_schema(schema_str: str) -> List[Tuple[str, str]]:
    """Parse schema from JSON or comma-separated format."""
    try:
        maybe = json.loads(schema_str)
        if isinstance(maybe, list):
            return [(name, typ) for name, typ in maybe]
    except json.JSONDecodeError:
        pass

    parts = schema_str.split(",")
    result: List[Tuple[str, str]] = []
    for p in parts:
        name, typ = p.split(":")
        result.append((name.strip(), typ.strip()))
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Convert CSV to custom columnar format"
    )
    parser.add_argument("input_csv", help="Input CSV file path")
    parser.add_argument("output_file", help="Output custom file path")
    parser.add_argument(
        "--schema",
        required=True,
        help=(
            "Schema definition, e.g. "
            '\"[[\'id\',\'int32\'],[\'value\',\'float64\'],[\'name\',\'string\']]\"\''
        ),
    )
    parser.add_argument(
        "--delimiter",
        default=",",
        help="CSV delimiter (default ',')",
    )

    args = parser.parse_args()
    schema = parse_schema(args.schema)
    write_from_csv(args.input_csv, args.output_file, schema, delimiter=args.delimiter)


if __name__ == "__main__":
    main()
