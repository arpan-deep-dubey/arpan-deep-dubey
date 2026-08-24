#!/usr/bin/env python3
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
    
    # 1. Total count
    header_match = re.search(r'([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year', html, re.IGNORECASE)
    total_count = int(header_match.group(1).replace(",", "")) if header_match else 0
    
    # 2. Extract cells
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

def generate_svg(total_count: int, cells: list) -> str:
    # Colors matching GitHub Dark Theme
    color_palette = {
        0: "#161b22",
        1: "#0e4429",
        2: "#006d32",
        3: "#26a641",
        4: "#39d353"
    }
    
    # Organize cells by week & day
    grid = {}
    month_positions = {}
    
    for cell in cells:
        row = cell["row"]
        col = cell["col"]
        grid[(row, col)] = cell
        
        # Calculate month labels position
        d = datetime.strptime(cell["date"], "%Y-%m-%d")
        if d.day == 1 or (d.day <= 7 and col not in month_positions.values()):
            month_name = d.strftime("%b")
            if month_name not in month_positions:
                month_positions[month_name] = col

    # Sort month labels by col
    sorted_months = sorted([(col, m) for m, col in month_positions.items()])
    
    # SVG Elements
    cells_xml = []
    for (row, col), cell in sorted(grid.items()):
        x = 46 + col * 13
        y = 44 + row * 13
        color = color_palette.get(cell["level"], "#161b22")
        cells_xml.append(f'  <rect x="{x}" y="{y}" width="10" height="10" rx="2" fill="{color}"/>')

    # Month Labels
    month_labels_xml = []
    for col, month_str in sorted_months:
        x = 46 + col * 13
        month_labels_xml.append(f'  <text x="{x}" y="36" fill="#7d8590" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Helvetica, Arial, sans-serif" font-size="10">{month_str}</text>')

    # Snake path traversing through the grid near non-zero clusters
    # Snake color: Crimson #FF3347 body, #FF6B78 highlight
    # Smooth continuous path over grid
    
    # Find non-zero cells for snake path
    active_points = [(46 + c["col"] * 13 + 5, 44 + c["row"] * 13 + 5) for c in cells if c["level"] > 0]
    
    # Standard snake path across grid if active_points are sparse
    snake_path_pts = []
    if len(active_points) >= 5:
        # Build path looping around active clusters
        snake_path_pts.extend(active_points)
        # Add smooth loop bounds
        snake_path_pts.append((46 + 50 * 13 + 5, 44 + 3 * 13 + 5))
        snake_path_pts.append((46 + 20 * 13 + 5, 44 + 6 * 13 + 5))
        snake_path_pts.append((46 + 5 * 13 + 5, 44 + 1 * 13 + 5))
    else:
        # Fallback path traversing across the calendar rows
        for c in range(0, 53, 4):
            snake_path_pts.append((46 + c * 13 + 5, 44 + 1 * 13 + 5))
            snake_path_pts.append((46 + c * 13 + 5, 44 + 5 * 13 + 5))

    path_d = f"M {snake_path_pts[0][0]},{snake_path_pts[0][1]}"
    for pt in snake_path_pts[1:]:
        path_d += f" L {pt[0]},{pt[1]}"

    svg_str = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 170" width="100%" height="170">
<style>
  .bg {{ fill: #0d1117; rx: 6px; }}
  .header-text {{ fill: #e6edf3; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 13px; font-weight: 600; }}
  .label-text {{ fill: #7d8590; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 10px; }}
  
  /* Crimson Snake Overlay Styling */
  .snake-glow {{
    fill: none;
    stroke: #FF3347;
    stroke-width: 8;
    stroke-linecap: round;
    stroke-linejoin: round;
    opacity: 0.35;
    filter: blur(2px);
  }}
  .snake-body {{
    fill: none;
    stroke: #FF3347;
    stroke-width: 6;
    stroke-linecap: round;
    stroke-linejoin: round;
    opacity: 0.9;
  }}
  .snake-highlight {{
    fill: none;
    stroke: #FF6B78;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
    opacity: 0.8;
  }}
  @keyframes snake-move {{
    0% {{ stroke-dashoffset: 2400; }}
    100% {{ stroke-dashoffset: 0; }}
  }}
  .animated-snake {{
    stroke-dasharray: 70 2400;
    animation: snake-move 16s linear infinite;
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

<!-- Native Contribution Cells Grid (Preserved Green Levels) -->
<g id="contribution-cells">
{chr(10).join(cells_xml)}
</g>

<!-- Animated Crimson Snake Layered Over Grid (Non-destructive overlay) -->
<path d="{path_d}" class="snake-glow animated-snake"/>
<path d="{path_d}" class="snake-body animated-snake"/>
<path d="{path_d}" class="snake-highlight animated-snake"/>

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
    print(f"Successfully generated composite snake calendar at '{out_file}'!")

if __name__ == "__main__":
    main()
