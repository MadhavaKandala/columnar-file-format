test_round_trip.py# tests/test_round_trip.py
import os
import tempfile
from columnar.writer import write_from_rows
from columnar.reader import read_as_rows


def test_round_trip():
    """Test that data round-trips correctly through write and read."""
    schema = [
        ("id", "int32"),
        ("value", "float64"),
        ("name", "string"),
    ]

    rows = [
        {"id": 1, "value": 1.5, "name": "alice"},
        {"id": 2, "value": 3.0, "name": "bob"},
        {"id": 3, "value": 2.5, "name": "charlie"},
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_file = os.path.join(tmp_dir, "data.cold")

        # Write data
        write_from_rows(out_file, rows, schema)

        # Read all data back
        all_rows = read_as_rows(out_file)
        assert all_rows == rows, f"Full read mismatch: {all_rows} != {rows}"

        # Test selective column read (column pruning)
        pruned_rows = read_as_rows(out_file, columns=["id", "name"])
        expected_pruned = [
            {"id": 1, "name": "alice"},
            {"id": 2, "name": "bob"},
            {"id": 3, "name": "charlie"},
        ]
        assert pruned_rows == expected_pruned, f"Pruned read mismatch: {pruned_rows} != {expected_pruned}"


if __name__ == "__main__":
    test_round_trip()
    print("All tests passed!")
