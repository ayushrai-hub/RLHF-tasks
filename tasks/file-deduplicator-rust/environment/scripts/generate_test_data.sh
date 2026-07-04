#!/bin/bash
# Generate test data for file deduplicator
# Usage: ./generate_test_data.sh <output_dir>

set -euo pipefail

OUTPUT_DIR="${1:-/app/data/sample_files}"
mkdir -p "$OUTPUT_DIR"

echo "Generating test data in $OUTPUT_DIR"

# Create unique files
echo "unique_content_1" > "$OUTPUT_DIR/unique_1.txt"
echo "unique_content_2" > "$OUTPUT_DIR/unique_2.txt"
echo "unique_content_3" > "$OUTPUT_DIR/unique_3.txt"

# Create duplicate groups (same content, different names)
echo "duplicate_group_a_content" > "$OUTPUT_DIR/dup_a_1.txt"
sleep 0.01
echo "duplicate_group_a_content" > "$OUTPUT_DIR/dup_a_2.txt"
sleep 0.01
echo "duplicate_group_a_content" > "$OUTPUT_DIR/dup_a_3.txt"

echo "duplicate_group_b_content" > "$OUTPUT_DIR/dup_b_1.txt"
sleep 0.01
echo "duplicate_group_b_content" > "$OUTPUT_DIR/dup_b_2.txt"

echo "duplicate_group_c_content" > "$OUTPUT_DIR/dup_c_1.txt"
sleep 0.01
echo "duplicate_group_c_content" > "$OUTPUT_DIR/dup_c_2.txt"
sleep 0.01
echo "duplicate_group_c_content" > "$OUTPUT_DIR/dup_c_3.txt"
sleep 0.01
echo "duplicate_group_c_content" > "$OUTPUT_DIR/dup_c_4.txt"

# Create zero-byte files (valid duplicates)
touch "$OUTPUT_DIR/empty_1.txt"
touch "$OUTPUT_DIR/empty_2.txt"
touch "$OUTPUT_DIR/empty_3.txt"

# Create hidden files
echo "hidden_content" > "$OUTPUT_DIR/.hidden_file.txt"

# Create subdirectory with duplicates
mkdir -p "$OUTPUT_DIR/subdir"
echo "subdir_content" > "$OUTPUT_DIR/subdir/file_1.txt"
echo "subdir_content" > "$OUTPUT_DIR/subdir/file_2.txt"
echo "unique_subdir" > "$OUTPUT_DIR/subdir/unique.txt"

echo "Test data generation complete."
echo "Files created:"
find "$OUTPUT_DIR" -type f | sort
