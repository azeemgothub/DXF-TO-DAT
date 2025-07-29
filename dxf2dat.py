import ezdxf

def extract_airfoil_from_dxf(dxf_filename, output_filename, file_format='selig'):
    """
    Convert DXF airfoil polylines to Selig/Lednicer .dat format.
    Preserves the actual trailing edge geometry (doesn't force y=0).
    Handles both single (closed) and double (upper/lower) polylines.
    """
    # Load DXF
    try:
        doc = ezdxf.readfile(dxf_filename)
    except IOError:
        raise ValueError(f"File '{dxf_filename}' not found or invalid DXF")
    except ezdxf.DXFStructureError:
        raise ValueError("Invalid DXF file structure")

    msp = doc.modelspace()
    polylines = []

    # Extract all polyline points
    for entity in msp:
        if entity.dxftype() in ('POLYLINE', 'LWPOLYLINE'):
            points = []
            if entity.dxftype() == 'LWPOLYLINE':
                points = [(vertex[0], vertex[1]) for vertex in entity]
            else:
                points = [(vertex.dxf.location[0], vertex.dxf.location[1]) 
                         for vertex in entity.vertices()]
            
            if points:
                polylines.append(points)

    # Process into upper/lower surfaces
    if len(polylines) == 2:
        polylines.sort(key=lambda pts: sum(y for _, y in pts)/len(pts), reverse=True)
        upper, lower = polylines
    elif len(polylines) == 1:
        all_pts = polylines[0]
        le_index = min(range(len(all_pts)), key=lambda i: all_pts[i][0])
        upper, lower = all_pts[:le_index+1], all_pts[le_index:]
    else:
        raise ValueError(f"Expected 1-2 polylines, found {len(polylines)}")

    # Normalize coordinates (LE at 0,0; TE x-coordinate at 1)
    min_x = min(x for x, _ in upper + lower)
    max_x = max(x for x, _ in upper + lower)
    le_point = next((x, y) for x, y in upper + lower if x == min_x)
    chord_length = max_x - min_x

    def normalize(x, y):
        return ((x - le_point[0]) / chord_length, (y - le_point[1]) / chord_length)

    # Sort upper surface from TE to LE (descending X)
    upper_norm = [normalize(x, y) for x, y in sorted(upper, key=lambda p: -p[0])]
    
    # Sort lower surface from LE to TE (ascending X)
    lower_norm = [normalize(x, y) for x, y in sorted(lower, key=lambda p: p[0])]

    # Find actual trailing edge points (max x-coordinate)
    te_upper = max(upper_norm, key=lambda p: p[0])
    te_lower = max(lower_norm, key=lambda p: p[0])

    # Write to file
    with open(output_filename, 'w') as f:
        if file_format == 'selig':
            # Single continuous loop (Upper TE→Upper→LE→Lower→Lower TE)
            combined = upper_norm + lower_norm[1:]  # Skip duplicate LE point
            f.write(f"{output_filename.replace('.dat', '')}\n")
            for x, y in combined:
                f.write(f"  {x:.6f}  {y:.6f}\n")

        elif file_format == 'lednicer':
            # Separate upper/lower with header
            f.write(f"{output_filename.replace('.dat', '').upper()} AIRFOIL\n")
            f.write(f"       {len(upper_norm)}.       {len(lower_norm)}.\n\n")
            
            # Upper surface (LE→TE)
            for x, y in reversed(upper_norm):
                f.write(f"  {x:.6f}  {y:.6f}\n")
            
            f.write("\n")
            
            # Lower surface (LE→TE)
            for x, y in lower_norm:
                f.write(f"  {x:.6f}  {y:.6f}\n")

    print(f"✓ Saved {len(upper_norm)+len(lower_norm)} points to {output_filename}")
    print(f"• LE moved to (0,0), TE at ({te_upper[0]:.4f},{te_upper[1]:.4f}) and ({te_lower[0]:.4f},{te_lower[1]:.4f})")
    print(f"• Format: {file_format.upper()}")

if __name__ == "__main__":
    print("==== DXF to Airfoil Converter ====")
    print("Converts DXF polylines to XFOIL (Selig) or XFLR5 (Lednicer) formats")
    print("Now preserves actual trailing edge geometry (no forced y=0)\n")
    
    # Interactive input
    dxf_file = input("Drag/DXF file here or type path: ").strip('"')
    dat_file = input("Output filename (e.g., 'naca2412.dat'): ").strip()
    if not dat_file.endswith('.dat'):
        dat_file += '.dat'
    
    while True:
        fmt = input("Format (S)elig or (L)ednicer? [S/L]: ").lower()
        if fmt in ('s', 'selig'):
            fmt = 'selig'
            break
        elif fmt in ('l', 'lednicer'):
            fmt = 'lednicer'
            break
        print("Invalid choice. Type 'S' or 'L'")

    try:
        extract_airfoil_from_dxf(dxf_file, dat_file, fmt)
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Check:")
        print("- DXF contains only airfoil polylines (no other geometry)")
        print("- File paths are correct")
    input("Press Enter to exit...")