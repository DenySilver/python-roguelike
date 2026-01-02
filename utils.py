import pygame
import heapq
from settings import *

class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.scroll = pygame.Vector2(0, 0)
        self.zoom = 1.0
        self.drag_start = None
        self.dragging = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.dragging = True
                self.drag_start = pygame.Vector2(event.pos)
            elif event.button == 4:
                self.zoom = min(self.zoom + 0.1, MAX_ZOOM)
            elif event.button == 5:
                self.zoom = max(self.zoom - 0.1, MIN_ZOOM)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False

    def update(self):
        if self.dragging:
            mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
            delta = mouse_pos - self.drag_start
            self.scroll += delta
            self.drag_start = mouse_pos

    def apply_rect(self, rect):
        screen_x = rect.x * self.zoom + self.scroll.x
        screen_y = rect.y * self.zoom + self.scroll.y
        return pygame.Rect(screen_x, screen_y, rect.width * self.zoom, rect.height * self.zoom)

    def center_on(self, target_x, target_y):
        self.scroll.x = WIDTH // 2 - (target_x * TILE_SIZE * self.zoom) - (TILE_SIZE * self.zoom // 2)
        self.scroll.y = HEIGHT // 2 - (target_y * TILE_SIZE * self.zoom) - (TILE_SIZE * self.zoom // 2)

def compute_fov(origin_x, origin_y, radius, map_data):
    visible = set()
    visible.add((origin_x, origin_y))
    multipliers = [
        (1, 0, 0, 1), (1, 0, 0, -1), (-1, 0, 0, 1), (-1, 0, 0, -1),
        (0, 1, 1, 0), (0, 1, -1, 0), (0, -1, 1, 0), (0, -1, -1, 0)
    ]
    for xx, xy, yx, yy in multipliers:
        _cast_light(origin_x, origin_y, radius, 1, 1.0, 0.0, xx, xy, yx, yy, map_data, visible)
    return visible

def _cast_light(cx, cy, radius, row, start_slope, end_slope, xx, xy, yx, yy, map_data, visible):
    if start_slope < end_slope:
        return
    radius_sq = radius * radius
    for j in range(row, radius + 1):
        dx = -j - 1
        dy = -j
        blocked = False
        while dx <= 0:
            dx += 1
            X, Y = cx + dx * xx + dy * xy, cy + dx * yx + dy * yy
            l_slope = (dx - 0.5) / (dy + 0.5)
            r_slope = (dx + 0.5) / (dy - 0.5)
            if start_slope < r_slope:
                continue
            if end_slope > l_slope:
                break
            if dx*dx + dy*dy <= radius_sq:
                visible.add((X, Y))
            is_blocked = False
            if (X, Y) not in map_data:
                is_blocked = True
            elif map_data[(X, Y)].block_sight:
                is_blocked = True
            if blocked:
                if is_blocked:
                    new_start = r_slope
                    continue
                else:
                    blocked = False
                    start_slope = new_start
            else:
                if is_blocked and j < radius:
                    blocked = True
                    _cast_light(cx, cy, radius, j + 1, start_slope, l_slope, xx, xy, yx, yy, map_data, visible)
                    new_start = r_slope
        if blocked:
            break

def get_path(start, goal, map_data, blocking_entities=None):
    if goal not in map_data:
        return []
    if blocking_entities is None:
        blocking_entities = set()
    frontier = []
    heapq.heappush(frontier, (0, start))
    came_from = {start: None}
    cost_so_far = {start: 0}
    while frontier:
        _, current = heapq.heappop(frontier)
        if current == goal:
            break
        cx, cy = current
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            next_node = (cx + dx, cy + dy)
            if next_node in map_data:
                tile = map_data[next_node]
                is_walkable = not tile.blocked
                if tile.type == 'door' and not tile.locked:
                    is_walkable = True
                if tile.type == 'wall':
                    is_walkable = False
                if next_node in blocking_entities and next_node != goal:
                    is_walkable = False
                if is_walkable:
                    new_cost = cost_so_far[current] + 1
                    if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                        cost_so_far[next_node] = new_cost
                        priority = new_cost + abs(goal[0] - next_node[0]) + abs(goal[1] - next_node[1])
                        heapq.heappush(frontier, (priority, next_node))
                        came_from[next_node] = current
    if goal not in came_from:
        return []
    current = goal
    path = []
    while current != start:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path

def has_line_of_sight(x1, y1, x2, y2, map_data):
    points = []
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    x, y = x1, y1
    sx = -1 if x1 > x2 else 1
    sy = -1 if y1 > y2 else 1
    if dx > dy:
        err = dx / 2.0
        while x != x2:
            if (x, y) in map_data and map_data[(x, y)].block_sight: return False
            points.append((x, y))
            err -= dy
            if err < 0:
                y += sy
                err += dx
            x += sx
    else:
        err = dy / 2.0
        while y != y2:
            if (x, y) in map_data and map_data[(x, y)].block_sight: return False
            points.append((x, y))
            err -= dx
            if err < 0:
                x += sx
                err += dy
            y += sy
    return True