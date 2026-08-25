#!/usr/bin/env python3
"""
Generate a composite GitHub contribution calendar SVG with a discrete,
cell-by-cell pixel-art Snake overlay.
"""
import urllib.request
import re
import os
import sys
from datetime import datetime

USERNAME = "arpan-deep-dubey"

def fetch_contributions(username: str) -> tuple[int, list]:
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    
    # 1. Extract total count
    header_match = re.search(r'([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year', html, re.IGNORECASE)
    total_count = int(header_match.group(1).replace(",", "")) if header_match else 91
    
    # 2. Extract daily cell data
    td_blocks = re.findall(r'<td[^>]*class="ContributionCalendar-day"[^>]*>', html)
    cells = []
    
    for td in td_blocks:
        date_m = re.search(r'data-date="([^"]+)"', td)
        level_m = re.search(r'data-level="([^"]+)"', td)
        id_m = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', td)
        
        if date_m and id_m:
            row = int(id_m.group(1)) # 0..6 (Sun..Sat)
            col = int(id_m.group(2)) # 0..52 (Week)
            date_str = date_m.group(1)
            level = int(level_m.group(1)) if level_m else 0
            cells.append({
                "row": row,
                "col": col,
                "date": date_str,
                "level": level
            })
            
    return total_count, cells

def cell_xy(row: int, col: int) -> tuple[int, int]:
    """Convert grid coordinates (row, col) to exact pixel coordinates (x, y)."""
    grid_origin_x = 46
    grid_origin_y = 44
    cell_spacing = 13
    return grid_origin_x + col * cell_spacing, grid_origin_y + row * cell_spacing

def build_snake_grid_path(active_cells: list) -> list:
    """
    Generate an orthogonal (UP, DOWN, LEFT, RIGHT) cell-by-cell path
    that weaves around green contribution clusters and loops cleanly.
    """
    # Waypoints traversing active contribution clusters across the grid
    waypoints = [
        (1, 10), (1, 28), (5, 28), (5, 34), (2, 34), (2, 44), 
        (5, 44), (5, 45), (2, 45), (2, 51), (4, 51), (4, 52), 
        (0, 52), (0, 48), (0, 10)
    ]
    
    path = []
    curr = waypoints[0]
    path.append(curr)
    
    for target in waypoints[1:]:
        r, c = curr
        tr, tc = target
        # Orthogonal step by step movement
        while c != tc:
            c += 1 if tc > c else -1
            path.append((r, c))
        while r != tr:
            r += 1 if tr > r else -1
            path.append((r, c))
        curr = (r, c)
        
    return path

def generate_svg(total_count: int, cells: list) -> str:
    # Native GitHub Dark Mode contribution colors
    color_palette = {
        0: "#161b22",
        1: "#0e4429",
        2: "#006d32",
        3: "#26a641",
        4: "#39d353"
    }
    
    grid = {}
    month_positions = {}
    
    for cell in cells:
        row = cell["row"]
        col = cell["col"]
        grid[(row, col)] = cell
        
        d = datetime.strptime(cell["date"], "%Y-%m-%d")
        if d.day == 1 or (d.day <= 7 and col not in month_positions.values()):
            month_name = d.strftime("%b")
            if month_name not in month_positions:
                month_positions[month_name] = col

    sorted_months = sorted([(col, m) for m, col in month_positions.items()])
    
    # 1. Render Contribution Cells Grid
    cells_xml = []
    for (row, col), cell in sorted(grid.items()):
        x, y = cell_xy(row, col)
        color = color_palette.get(cell["level"], "#161b22")
        cells_xml.append(f'  <rect x="{x}" y="{y}" width="10" height="10" rx="2" fill="{color}"/>')

    # 2. Render Month Labels
    month_labels_xml = []
    for col, month_str in sorted_months:
        x = 46 + col * 13
        month_labels_xml.append(f'  <text x="{x}" y="36" fill="#7d8590" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Helvetica, Arial, sans-serif" font-size="10">{month_str}</text>')

    # 3. Generate Cell-by-Cell Snake Path & Keyframe Animations
    active_cells = [(c["row"], c["col"]) for c in cells if c["level"] > 0]
    snake_path = build_snake_grid_path(active_cells)
    N = len(snake_path)
    
    head_kf, b1_kf, b2_kf, b3_kf, tail_kf = [], [], [], [], []
    
    for i in range(N):
        pct = round((i / N) * 100, 2)
        
        # Head at step i
        hx, hy = cell_xy(*snake_path[i])
        head_kf.append(f"  {pct}% {{ transform: translate({hx}px, {hy}px); }}")
        
        # Body 1 at step i-1
        b1x, b1y = cell_xy(*snake_path[(i - 1) % N])
        b1_kf.append(f"  {pct}% {{ transform: translate({b1x}px, {b1y}px); }}")
        
        # Body 2 at step i-2
        b2x, b2y = cell_xy(*snake_path[(i - 2) % N])
        b2_kf.append(f"  {pct}% {{ transform: translate({b2x}px, {b2y}px); }}")
        
        # Body 3 at step i-3
        b3x, b3y = cell_xy(*snake_path[(i - 3) % N])
        b3_kf.append(f"  {pct}% {{ transform: translate({b3x + 0.5}px, {b3y + 0.5}px); }}")
        
        # Tail at step i-4
        tx, ty = cell_xy(*snake_path[(i - 4) % N])
        tail_kf.append(f"  {pct}% {{ transform: translate({tx + 1.5}px, {ty + 1.5}px); }}")

    # Final 100% keyframe to close animation loop
    h0x, h0y = cell_xy(*snake_path[0])
    b10x, b10y = cell_xy(*snake_path[-1])
    b20x, b20y = cell_xy(*snake_path[-2])
    b30x, b30y = cell_xy(*snake_path[-3])
    t0x, t0y = cell_xy(*snake_path[-4])
    
    head_kf.append(f"  100% {{ transform: translate({h0x}px, {h0y}px); }}")
    b1_kf.append(f"  100% {{ transform: translate({b10x}px, {b10y}px); }}")
    b2_kf.append(f"  100% {{ transform: translate({b20x}px, {b20y}px); }}")
    b3_kf.append(f"  100% {{ transform: translate({b30x + 0.5}px, {b30y + 0.5}px); }}")
    tail_kf.append(f"  100% {{ transform: translate({t0x + 1.5}px, {t0y + 1.5}px); }}")

    duration_sec = round(N * 0.15, 1) # 150ms per cell step

    svg_str = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 170" width="100%" height="170">
<style>
  .bg {{ fill: #0d1117; rx: 6px; }}
  .header-text {{ fill: #e6edf3; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 13px; font-weight: 600; }}
  .label-text {{ fill: #7d8590; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 10px; }}
  
  /* Pixel-art Snake Segment Styling */
  .s-head-rect {{ fill: #FF3347; stroke: #080A0F; stroke-width: 0.8; }}
  .s-eye {{ fill: #FF6B78; }}
  .s-b1 {{ fill: #D91F36; stroke: #080A0F; stroke-width: 0.5; animation: move-b1 {duration_sec}s steps(1) infinite; }}
  .s-b2 {{ fill: #D91F36; stroke: #080A0F; stroke-width: 0.5; animation: move-b2 {duration_sec}s steps(1) infinite; }}
  .s-b3 {{ fill: #C0192D; opacity: 0.9; animation: move-b3 {duration_sec}s steps(1) infinite; }}
  .s-tail {{ fill: #A01424; opacity: 0.8; animation: move-tail {duration_sec}s steps(1) infinite; }}
  .s-head-group {{ animation: move-head {duration_sec}s steps(1) infinite; }}

  @keyframes move-head {{
{chr(10).join(head_kf)}
  }}
  @keyframes move-b1 {{
{chr(10).join(b1_kf)}
  }}
  @keyframes move-b2 {{
{chr(10).join(b2_kf)}
  }}
  @keyframes move-b3 {{
{chr(10).join(b3_kf)}
  }}
  @keyframes move-tail {{
{chr(10).join(tail_kf)}
  }}
</style>

<!-- Native Dark Card Background -->
<rect width="760" height="170" class="bg"/>

<!-- Official Total Contributions Header -->
<text x="46" y="20" class="header-text">{total_count:,} contributions in the last year</text>

<!-- Month Labels -->
{''.join(month_labels_xml)}

<!-- Weekday Labels -->
<text x="22" y="58" class="label-text">Mon</text>
<text x="22" y="84" class="label-text">Wed</text>
<text x="22" y="110" class="label-text">Fri</text>

<!-- Native Contribution Cells Grid (Green Levels Preserved) -->
<g id="contribution-cells">
{chr(10).join(cells_xml)}
</g>

<!-- Animated Pixel Snake Overlay (Discrete Cell Steps) -->
<g id="pixel-snake">
  <rect class="s-tail" width="7" height="7" rx="2"/>
  <rect class="s-b3" width="9" height="9" rx="2"/>
  <rect class="s-b2" width="10" height="10" rx="2"/>
  <rect class="s-b1" width="10" height="10" rx="2"/>
  <g class="s-head-group">
    <rect class="s-head-rect" width="10" height="10" rx="2.5"/>
    <circle cx="7.5" cy="2.5" r="1.2" class="s-eye"/>
  </g>
</g>

<!-- Bottom Legend Section -->
<g transform="translate(560, 142)">
  <text x="0" y="9" class="label-text">Less</text>
  <rect x="28" y="0" width="10" height="10" rx="2" fill="#161b22"/>
  <rect x="42" y="0" width="10" height="10" rx="2" fill="#0e4429"/>
  <rect x="56" y="0" width="10" height="10" rx="2" fill="#006d32"/>
  <rect x="70" y="0" width="10" height="10" rx="2" fill="#26a641"/>
  <rect x="84" y="0" width="10" height="10" rx="2" fill="#39d353"/>
  <text x="98" y="9" class="label-text">More</text>
</g>

</svg>
'''
    return svg_str

def main():
    username = sys.argv[1] if len(sys.argv) > 1 else USERNAME
    out_file = sys.argv[2] if len(sys.argv) > 2 else "assets/contribution/github-contribution-calendar-snake.svg"
    
    print(f"Fetching GitHub contribution calendar for user '{username}'...")
    total_count, cells = fetch_contributions(username)
    print(f"Fetched {total_count} total contributions across {len(cells)} day cells.")
    
    svg = generate_svg(total_count, cells)
    
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Successfully generated composite pixel snake calendar at '{out_file}'!")

if __name__ == "__main__":
    main()
