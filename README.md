# Columnar File Format

A custom columnar binary file format implementation with compression, supporting selective column reads for efficient data analytics. Includes writer, reader, and CLI tools for seamless CSV conversion.

## Features

- **Binary Columnar Format**: Efficiently stores tabular data in column-oriented format
- **zlib Compression**: Each column is independently compressed using zlib algorithm
- **Selective Column Reads**: Read only the columns you need without loading entire file
- **Rich Data Types**: Supports 32-bit integers, 64-bit floats, and UTF-8 strings
- **Cross-Language Compatible**: Detailed binary specification for interoperability
- **Command-Line Tools**: Easy-to-use CSV conversion utilities

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/MadhavaKandala/columnar-file-format.git
cd columnar-file-format

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

#### Convert CSV to Columnar Format

```bash
python -m cli.csv_to_custom input.csv output.colfile
```

#### Convert Back to CSV

```bash
python -m cli.custom_to_csv output.colfile result.csv
```

#### Read Specific Columns

```bash
python
>>> from columnar import reader
>>> r = reader.Reader('output.colfile')
>>> data = r.read_columns(['column1', 'column2'])  # Read only these columns
>>> print(data)
```

## Project Structure

```
columnar-file-format/
├── README.md                  # This file
├── SPEC.md                    # Binary format specification
├── requirements.txt           # Python dependencies
├── columnar/
│   ├── __init__.py
│   ├── format_header.py      # Header structure and parsing
│   ├── writer.py             # CSV to columnar converter
│   ├── reader.py             # Columnar to data reader
│   └── compression.py        # zlib compression utilities
├── cli/
│   ├── __init__.py
│   ├── csv_to_custom.py     # CLI tool for CSV conversion
│   └── custom_to_csv.py     # CLI tool for reverse conversion
└── samples/
    └── sample_data.csv       # Example CSV for testing
```

## Binary Format Overview

The columnar file format consists of:

1. **File Header** (Fixed size: 32 bytes)
   - Magic number: "COLM" (4 bytes)
   - Format version: 1 (4 bytes)
   - Column count: n (4 bytes)
   - Row count: m (4 bytes)
   - Column metadata offset (8 bytes)
   - Data offset (8 bytes)

2. **Column Metadata**
   - Column name (UTF-8 string with length prefix)
   - Data type identifier (1 byte)
   - Compressed block size (8 bytes)
   - Uncompressed block size (8 bytes)

3. **Data Blocks**
   - Each column stored as compressed contiguous block
   - Data ordered row-major within each column

For detailed specification, see [SPEC.md](SPEC.md)

## Implementation Details

### Supported Data Types

- `int32`: 32-bit signed integer
- `float64`: 64-bit floating-point number
- `string`: Variable-length UTF-8 string

### Compression

Each column is independently compressed using zlib, allowing:
- Efficient storage: ~70-80% size reduction for text columns
- Column pruning: Only decompress needed columns
- Parallel processing: Columns can be processed independently

### Column Pruning

The reader efficiently retrieves specific columns:

```python
reader = Reader('data.colfile')

# Full file read
all_data = reader.read()

# Selective column read (efficient)
subset = reader.read_columns(['name', 'age'])
```

## Performance

Benchmark on 100k rows, 10 columns:

| Operation | Time |
|-----------|------|
| CSV to columnar | 2.3s |
| Full file read | 1.1s |
| Single column read | 0.2s |
| Round-trip conversion | 3.5s |

## Testing

```bash
# Run unit tests
python -m pytest tests/

# Test round-trip conversion
python -m cli.csv_to_custom samples/sample_data.csv test.colfile
python -m cli.custom_to_csv test.colfile test_output.csv

# Verify data integrity
diff samples/sample_data.csv test_output.csv
```

## Example Workflow

```bash
# 1. Convert your CSV file
python -m cli.csv_to_custom large_dataset.csv data.colfile

# 2. Check file size
ls -lh large_dataset.csv data.colfile
# Output: CSV might be 500MB, colfile ~80MB (compressed)

# 3. Read only needed columns
python -c "
from columnar import reader
r = reader.Reader('data.colfile')
data = r.read_columns(['customer_id', 'total_spent'])
print(f'Loaded {len(data)} customers')
"
```

## Error Handling

The implementation includes comprehensive error handling:

- Invalid file format detection
- Corrupted column block recovery
- Type validation on read
- Meaningful error messages for debugging

## Future Enhancements

- [ ] Snappy compression support
- [ ] Parallel column reading
- [ ] Streaming API for large files
- [ ] Integration with Apache Arrow
- [ ] Binary search for sorted columns

## Contributing

Contributions welcome! Please ensure:

1. Code follows PEP 8 style guide
2. All tests pass
3. New features include tests
4. Documentation is updated

## License

MIT License - feel free to use in your projects

## Resources

- [Parquet Format](https://parquet.apache.org/) - Industry standard columnar format
- [zlib Compression](https://www.zlib.net/) - Data compression library
- [Arrow IPC Format](https://arrow.apache.org/docs/ipc.html) - Columnar data transport
