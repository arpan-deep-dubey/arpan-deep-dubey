#!/usr/bin/env python3
"""
Generate an authentic GitHub contribution calendar animated GIF
with a discrete cell-by-cell pixel-art Snake overlay that navigates
exclusively through EMPTY cells around green contribution clusters.
"""
import urllib.request
import re
import os
import sys
from datetime import datetime
from collections import deque
from PIL import Image, ImageDraw, ImageFont

USERNAME = "arpan-deep-dubey"

def fetch_contributions(username: str) -> tuple[int, list]:
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    
    # 1. Extract total count
    header_match = re.search(r'([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year', html, re.IGNORECASE)
    total_count = int(header_match.group(1).replace(",", "")) if header_match else 92
    
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

def bfs_path(start: tuple, goal: tuple, blocked: set) -> list:
    """Find shortest path on empty cells from start to goal using BFS."""
    if start in blocked or goal in blocked:
        return None
    queue = deque([[start]])
    visited = {start}
    
    while queue:
        path = queue.popleft()
        r, c = path[-1]
        if (r, c) == goal:
            return path
        
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 7 and 0 <= nc < 53:
                if (nr, nc) not in blocked and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    queue.append(path + [(nr, nc)])
    return None

def build_snake_grid_path(blocked_cells: set) -> list:
    """
    Generate an orthogonal (UP, DOWN, LEFT, RIGHT) cell-by-cell path
    that weaves strictly through EMPTY grid cells around green contribution clusters.
    Uses dynamic reachability checks for 100% robust pathfinding.
    """
    cols_order = [5, 12, 20, 27, 33, 38, 43, 48, 50, 48, 43, 38, 33, 27, 20, 12, 5]
    
    current = None
    for c in cols_order:
        for r in range(7):
            if (r, c) not in blocked_cells:
                current = (r, c)
                break
        if current:
            break
            
    full_path = [current]
    
    for idx, c in enumerate(cols_order[1:]):
        empty_rows = [r for r in range(7) if (r, c) not in blocked_cells]
        if idx % 2 == 1:
            empty_rows.reverse()
            
        for r in empty_rows:
            target = (r, c)
            sub = bfs_path(current, target, blocked_cells)
            if sub:
                full_path.extend(sub[1:])
                current = target
                break
                
    final_sub = bfs_path(current, full_path[0], blocked_cells)
    if final_sub:
        full_path.extend(final_sub[1:])

    return full_path

def render_base_calendar(total_count: int, cells: list) -> Image.Image:
    width, height = 760, 170
    base = Image.new("RGBA", (width, height), "#0d1117")
    draw = ImageDraw.Draw(base)
    
    try:
        font_header = ImageFont.truetype("arial.ttf", 13)
        font_label = ImageFont.truetype("arial.ttf", 10)
    except IOError:
        font_header = ImageFont.load_default()
        font_label = ImageFont.load_default()

    # Header text
    draw.text((46, 12), f"{total_count:,} contributions in the last year", fill="#e6edf3", font=font_header)
    
    # Weekday labels
    draw.text((22, 54), "Mon", fill="#7d8590", font=font_label)
    draw.text((22, 80), "Wed", fill="#7d8590", font=font_label)
    draw.text((22, 106), "Fri", fill="#7d8590", font=font_label)
    
    # Color palette matching GitHub Dark Mode
    color_palette = {
        0: "#161b22",
        1: "#0e4429",
        2: "#006d32",
        3: "#26a641",
        4: "#39d353"
    }
    
    # Render Month Labels & Grid Cells
    month_positions = {}
    for cell in cells:
        r, c = cell["row"], cell["col"]
        x, y = cell_xy(r, c)
        color = color_palette.get(cell["level"], "#161b22")
        draw.rounded_rectangle([x, y, x + 10, y + 10], radius=2, fill=color)
        
        d = datetime.strptime(cell["date"], "%Y-%m-%d")
        if d.day == 1 or (d.day <= 7 and c not in month_positions.values()):
            m_str = d.strftime("%b")
            if m_str not in month_positions:
                month_positions[m_str] = c

    for m_str, c in sorted([(m, c) for m, c in month_positions.items()], key=lambda x: x[1]):
        x = 46 + c * 13
        draw.text((x, 30), m_str, fill="#7d8590", font=font_label)

    # Bottom Legend Section
    legend_x = 560
    legend_y = 142
    draw.text((legend_x, legend_y), "Less", fill="#7d8590", font=font_label)
    for idx, lvl in enumerate([0, 1, 2, 3, 4]):
        lx = legend_x + 28 + idx * 14
        draw.rounded_rectangle([lx, legend_y + 1, lx + 10, legend_y + 11], radius=2, fill=color_palette[lvl])
    draw.text((legend_x + 98, legend_y), "More", fill="#7d8590", font=font_label)

    return base

def draw_snake_frame(base_img: Image.Image, path: list, frame_idx: int) -> Image.Image:
    frame = base_img.copy()
    draw = ImageDraw.Draw(frame)
    N = len(path)
    
    # 5 Snake segments: Head, Body1, Body2, Body3, Tail
    head_r, head_c = path[frame_idx]
    b1_r, b1_c = path[(frame_idx - 1) % N]
    b2_r, b2_c = path[(frame_idx - 2) % N]
    b3_r, b3_c = path[(frame_idx - 3) % N]
    tail_r, tail_c = path[(frame_idx - 4) % N]

    # Draw Tail (7x7 px)
    tx, ty = cell_xy(tail_r, tail_c)
    draw.rounded_rectangle([tx + 1, ty + 1, tx + 8, ty + 8], radius=2, fill="#A01424")

    # Draw Body 3 (9x9 px)
    b3x, b3y = cell_xy(b3_r, b3_c)
    draw.rounded_rectangle([b3x, b3y, b3x + 9, b3y + 9], radius=2, fill="#C0192D")

    # Draw Body 2 (10x10 px)
    b2x, b2y = cell_xy(b2_r, b2_c)
    draw.rounded_rectangle([b2x, b2y, b2x + 10, b2y + 10], radius=2, fill="#D91F36", outline="#080A0F", width=1)

    # Draw Body 1 (10x10 px)
    b1x, b1y = cell_xy(b1_r, b1_c)
    draw.rounded_rectangle([b1x, b1y, b1x + 10, b1y + 10], radius=2, fill="#D91F36", outline="#080A0F", width=1)

    # Draw Head (10x10 px)
    hx, hy = cell_xy(head_r, head_c)
    draw.rounded_rectangle([hx, hy, hx + 10, hy + 10], radius=2.5, fill="#FF3347", outline="#080A0F", width=1)
    
    # Directional eye indicator
    next_r, next_c = path[(frame_idx + 1) % N]
    dr = next_r - head_r
    dc = next_c - head_c
    
    if dc > 0: # Moving Right
        draw.ellipse([hx + 7, hy + 2, hx + 9, hy + 4], fill="#FF6B78")
    elif dc < 0: # Moving Left
        draw.ellipse([hx + 1, hy + 2, hx + 3, hy + 4], fill="#FF6B78")
    elif dr > 0: # Moving Down
        draw.ellipse([hx + 7, hy + 7, hx + 9, hy + 9], fill="#FF6B78")
    else: # Moving Up
        draw.ellipse([hx + 7, hy + 1, hx + 9, hy + 3], fill="#FF6B78")

    return frame

def generate_snake_animation(total_count: int, cells: list, gif_out: str):
    base_img = render_base_calendar(total_count, cells)
    
    # Identify all green contribution cells as blocked obstacles
    blocked_cells = set((c["row"], c["col"]) for c in cells if c["level"] > 0)
    print(f"Identified {len(blocked_cells)} green contribution cells as blocked obstacles.")
    
    # Build path through EMPTY cells only
    path = build_snake_grid_path(blocked_cells)
    N = len(path)
    print(f"Generated obstacle-avoiding snake path across {N} steps.")

    # MANDATORY VALIDATION TEST: Assert 0 overlap across all frames & segments
    for idx in range(N):
        snake_segments = [
            path[idx],
            path[(idx - 1) % N],
            path[(idx - 2) % N],
            path[(idx - 3) % N],
            path[(idx - 4) % N]
        ]
        overlaps = [seg for seg in snake_segments if seg in blocked_cells]
        if overlaps:
            raise RuntimeError(f"VALIDATION FAILURE: Frame {idx} overlaps green cell(s): {overlaps}")

    print("VALIDATION SUCCESS: Verified 100% ZERO OVERLAP across all animation frames!")

    frames = []
    print(f"Rendering {N} animation frames for Snake...")
    
    for idx in range(N):
        frame = draw_snake_frame(base_img, path, idx)
        p_frame = frame.convert("P", palette=Image.ADAPTIVE)
        frames.append(p_frame)

    os.makedirs(os.path.dirname(gif_out), exist_ok=True)
    frames[0].save(
        gif_out,
        save_all=True,
        append_images=frames[1:],
        duration=150,
        loop=0
    )
    print(f"Saved animated GIF at '{gif_out}'!")

    # Export 10 debug frames for visual inspection
    debug_dir = "scratch/debug_frames"
    os.makedirs(debug_dir, exist_ok=True)
    step_gap = max(1, N // 10)
    for i in range(10):
        frame_idx = (i * step_gap) % N
        debug_frame = draw_snake_frame(base_img, path, frame_idx)
        debug_path = os.path.join(debug_dir, f"frame_{i+1:02d}.png")
        debug_frame.save(debug_path)
        print(f"Saved debug frame {i+1} at '{debug_path}'")

def main():
    username = sys.argv[1] if len(sys.argv) > 1 else USERNAME
    gif_out = sys.argv[2] if len(sys.argv) > 2 else "assets/contribution/github-contribution-calendar-snake.gif"
    
    print(f"Fetching GitHub contribution calendar for user '{username}'...")
    total_count, cells = fetch_contributions(username)
    print(f"Fetched {total_count} total contributions across {len(cells)} day cells.")
    
    generate_snake_animation(total_count, cells, gif_out)

if __name__ == "__main__":
    main()
