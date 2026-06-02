#!/usr/bin/env python3
"""
Patch a 3DGS PLY file to add missing f_rest_* spherical harmonics coefficients.

Some PLY exporters produce SH degree 0 (no f_rest, only f_dc).
aiSim's GS3D renderer requires at minimum f_rest_0 through f_rest_44 (SH degree 3).

This script appends 45 zero-valued float32 per vertex and updates the header,
converting a degree-0 PLY to degree-3 without any loss of visual quality
(all-zero f_rest means no view-dependent color effects).

Usage:
    python3 patch_ply_sh.py --input <input.ply> --output <output.ply>
"""

import argparse
import os
import struct
import sys

# SH degree 3 → 3 channels × ((3+1)^2 - 1) = 45 f_rest coefficients
F_REST_COUNT = 45
FLOAT_SIZE = 4
BYTES_PER_VERTEX_ORIGINAL = 17 * FLOAT_SIZE   # x,y,z, nx,ny,nz, f_dc_0-2, opacity, scale_0-2, rot_0-3
BYTES_PER_VERTEX_PATCHED = (17 + F_REST_COUNT) * FLOAT_SIZE
ZERO_PADDING = bytes(F_REST_COUNT * FLOAT_SIZE)  # 180 bytes of zeros


def parse_header(filepath: str):
    """Read the PLY header and return (header_lines, header_end_offset, vertex_count)."""
    with open(filepath, 'rb') as f:
        raw = f.read(4096)  # Headers are typically < 2KB

    # Find end_header position
    header_text = raw.decode('ascii', errors='replace')
    end_idx = header_text.find('end_header\n')
    if end_idx == -1:
        raise ValueError("Malformed PLY: 'end_header' not found")
    header_end_offset = end_idx + len('end_header\n')

    lines = [l for l in header_text[:end_idx].split('\n') if l.strip()]

    vertex_count = 0
    for line in lines:
        if line.startswith('element vertex '):
            vertex_count = int(line.split()[2])

    return lines, header_end_offset, vertex_count


def patch_ply(input_path: str, output_path: str):
    """Stream through input PLY, appending zero f_rest to each vertex."""

    header_lines, header_offset, vertex_count = parse_header(input_path)
    if vertex_count == 0:
        print("Error: no vertex element found in PLY header")
        sys.exit(1)

    print(f"Input:  {input_path}  ({os.path.getsize(input_path) / 1e9:.2f} GB)")
    print(f"Vertices: {vertex_count:,}")
    print(f"Adding {F_REST_COUNT} f_rest_* coefficients (SH degree 3)")

    # Build new header: insert f_rest properties before end_header
    new_header_lines = list(header_lines)
    for i in range(F_REST_COUNT):
        new_header_lines.append(f'property float f_rest_{i}')
    new_header_lines.append('end_header')
    new_header = '\n'.join(new_header_lines) + '\n'

    # Verify new header
    expected_size = vertex_count * BYTES_PER_VERTEX_PATCHED + len(new_header.encode('ascii'))
    print(f"Output: {output_path}  (~{expected_size / 1e9:.2f} GB)")

    with open(input_path, 'rb') as fin, open(output_path, 'wb') as fout:
        # Write new header
        fout.write(new_header.encode('ascii'))

        # Skip old header in input
        fin.seek(header_offset)

        # Stream vertices
        bytes_read = 0
        bytes_total = vertex_count * BYTES_PER_VERTEX_ORIGINAL
        report_interval = max(1, vertex_count // 20)  # report every 5%

        for i in range(vertex_count):
            vertex_data = fin.read(BYTES_PER_VERTEX_ORIGINAL)
            if len(vertex_data) < BYTES_PER_VERTEX_ORIGINAL:
                print(f"\nWarning: unexpected EOF at vertex {i}")
                break

            fout.write(vertex_data)
            fout.write(ZERO_PADDING)

            bytes_read += BYTES_PER_VERTEX_ORIGINAL
            if (i + 1) % report_interval == 0:
                pct = (i + 1) * 100 // vertex_count
                print(f"  {pct}% ({i + 1:,} / {vertex_count:,})", end='\r')

    print(f"\nDone. Output size: {os.path.getsize(output_path) / 1e9:.2f} GB")


def main():
    parser = argparse.ArgumentParser(
        description="Patch 3DGS PLY: add missing f_rest_* SH coefficients"
    )
    parser.add_argument('--input', '-i', required=True, help='Input PLY file (SH degree 0)')
    parser.add_argument('--output', '-o', required=True, help='Output PLY file (SH degree 3)')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: input file not found: {args.input}")
        sys.exit(1)

    patch_ply(args.input, args.output)


if __name__ == '__main__':
    main()
