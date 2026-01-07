# cli/csv_to_custom.py
import argparse
import json
from typing import List, Tuple

from columnar.writer import write_from_csv


def parse_schema(schema_str: str) -> List[Tuple[str, str]]:
    """Parse schema from JSON or colon-separated format."""
    try:
        maybe = json.loads(schema_str)
        if isinstance(maybe, list):
            return [(name, typ) for name, typ in maybe]
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Try colon-separated format: id:int32,value:float64
    parts = schema_str.split(",")
    result: List[Tuple[str, str]] = []
    for p in parts:
        p = p.strip()
        if ":" not in p:
            raise ValueError(f"Invalid format: {p}. Use 'name:type'")
        name, typ = p.split(":")
        result.append((name.strip(), typ.strip()))
    return result


def main():
    parser = argparse.ArgumentParser(description="Convert CSV to columnar")
    parser.add_argument("input_csv", help="Input CSV file")
    parser.add_argument("output_file", help="Output file")
    parser.add_argument(
        "--schema",
        required=True,
        help='JSON: [["id","int32"],["name","string"]] or id:int32,name:string',
    )
    parser.add_argument("--delimiter", default=",", help="CSV delimiter")

    args = parser.parse_args()
    schema = parse_schema(args.schema)
    write_from_csv(args.input_csv, args.output_file, schema, delimiter=args.delimiter)
    print(f"✅ Converted {args.input_csv} -> {args.output_file}")


if __name__ == "__main__":
    main()
