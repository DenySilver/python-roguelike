import random
import pygame
from settings import *

class Room:
    def __init__(self, rect, type_='normal'):
        self.rect = rect
        self.type = type_
        self.center = rect.center

class Tile:
    def __init__(self, x, y, type_):
        self.x, self.y = x, y
        self.type = type_
        self.visible = False
        self.explored = False
        self.variant = random.randint(0, 2)
        self.is_open = False
        self.locked = False
        self.key_color = None

    @property
    def blocked(self):
        if self.type == 'wall': return True
        if self.type == 'door' and not self.is_open: return True
        return False

    @blocked.setter
    def blocked(self, val):
        if self.type == 'door':
            self.is_open = not val

    @property
    def block_sight(self):
        if self.type == 'wall': return True
        if self.type == 'door' and not self.is_open: return True
        return False

    @block_sight.setter
    def block_sight(self, val):
        if self.type == 'door':
            self.is_open = not val

class MapGenerator:
    def __init__(self, level):
        self.level = level
        self.width = 40 + (level // LEVELS_PER_BIOME) * LEVELS_PER_BIOME
        self.height = 40 + (level // LEVELS_PER_BIOME) * LEVELS_PER_BIOME
        self.tiles = {}
        self.rooms = []

    def generate(self):
        for y in range(self.height):
            for x in range(self.width):
                self.tiles[(x, y)] = Tile(x, y, 'void')
        player_start = (0, 0)
        exit_pos = (0, 0)
        enemies = []
        items = []
        chests = []
        is_maze_level = (self.level % LEVELS_PER_BIOME == 0)
        print(f"[MapGen] Level: {self.level} | Max: {MAX_LEVEL} | Maze?: {is_maze_level}")
        if is_maze_level:
            player_start, exit_pos, items, enemies = self._generate_maze_level()
        else:
            player_start, exit_pos, items, enemies, chests = self._generate_loop_level()
        self.tiles[player_start] = Tile(player_start[0], player_start[1], 'stairs_up')
        if self.level < MAX_LEVEL:
            self.tiles[exit_pos] = Tile(exit_pos[0], exit_pos[1], 'stairs_down')
        else:
            print(f"[MapGen] Spawning WIN ITEM at {exit_pos}")
            self.tiles[exit_pos] = Tile(exit_pos[0], exit_pos[1], 'floor')
            items.append({'pos': exit_pos, 'name': WIN_ITEM, 'color': None})
        return self.tiles, player_start, exit_pos, enemies, items, chests

    def _generate_loop_level(self):
        sect_w = MAP_GEN['SECT_WIDTH']
        sect_h = MAP_GEN['SECT_HEIGHT']
        grid_w = self.width // sect_w
        grid_h = self.height // sect_h
        connections = []
        visited = {(0,0)}
        stack = [(0,0)]
        #======
        while stack:
            cx, cy = stack[-1]
            neighbors = []
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                nx, ny = cx+dx, cy+dy
                if 0 <= nx < grid_w and 0 <= ny < grid_h:
                    if (nx, ny) not in visited:
                        neighbors.append((nx, ny))
            if neighbors:
                nx, ny = random.choice(neighbors)
                connections.append( ((cx, cy), (nx, ny)) )
                visited.add((nx, ny))
                stack.append((nx, ny))
            else:
                stack.pop()
        #======
        for _ in range(int(grid_w * grid_h * MAP_GEN['EXTRA_CONNECTIONS_FACTOR'])):
            rx, ry = random.randint(0, grid_w-1), random.randint(0, grid_h-1)
            dirs = [(0,1), (1,0)]
            dx, dy = random.choice(dirs)
            nx, ny = rx+dx, ry+dy
            if 0 <= nx < grid_w and 0 <= ny < grid_h:
                if ((rx, ry), (nx, ny)) not in connections and ((nx, ny), (rx, ry)) not in connections:
                    connections.append( ((rx, ry), (nx, ny)) )
        rooms_map = {}
        #======
        for gy in range(grid_h):
            for gx in range(grid_w):
                rw = random.randint(MAP_GEN['MIN_ROOM_SIZE'], sect_w - 2)
                rh = random.randint(MAP_GEN['MIN_ROOM_SIZE'], sect_h - 2)
                rx = gx * sect_w + random.randint(1, sect_w - rw - 1)
                ry = gy * sect_h + random.randint(1, sect_h - rh - 1)
                room_rect = pygame.Rect(rx, ry, rw, rh)
                rtype = 'normal'
                if random.random() < MAP_GEN['TREASURE_ROOM_CHANCE']: rtype = 'treasure'
                new_room = Room(room_rect, rtype)
                rooms_map[(gx, gy)] = new_room
                self.rooms.append(new_room)
                for y in range(room_rect.top, room_rect.bottom):
                    for x in range(room_rect.left, room_rect.right):
                        self.tiles[(x, y)] = Tile(x, y, 'floor')
        #======
        for (p1, p2) in connections:
            r1 = rooms_map[p1]
            r2 = rooms_map[p2]
            c1 = r1.center
            c2 = r2.center
            if random.random() < MAP_GEN['TUNNEL_RANDOMNESS']:
                self._tunnel_h(c1[0], c2[0], c1[1])
                self._tunnel_v(c1[1], c2[1], c2[0])
            else:
                self._tunnel_v(c1[1], c2[1], c1[0])
                self._tunnel_h(c1[0], c2[0], c2[1])
        #======
        self._place_walls()
        self._place_doors()
        start_room = random.choice(self.rooms)
        start_room.type = 'start'
        best_exit = None
        max_dist = 0
        for room in self.rooms:
            if room == start_room: continue
            dx = room.center[0] - start_room.center[0]
            dy = room.center[1] - start_room.center[1]
            dist = (dx**2 + dy**2)**0.5
            if dist > max_dist:
                max_dist = dist
                best_exit = room
        if best_exit:
            best_exit.type = 'exit'
        else:
            self.rooms[-1].type = 'exit'
            best_exit = self.rooms[-1]
        player_start = start_room.center
        exit_pos = best_exit.center
        items, enemies, chests = self._populate_standard_level(player_start, exit_pos)
        return player_start, exit_pos, items, enemies, chests

    def _generate_maze_level(self):
        maze_w = self.width // 2
        maze_h = self.height // 2
        visited = set()
        stack = [(0, 0)]
        visited.add((0, 0))
        adjacency = {}
        #======
        while stack:
            cx, cy = stack[-1]
            neighbors = []
            directions = [(0,1), (0,-1), (1,0), (-1,0)]
            random.shuffle(directions)
            for dx, dy in directions:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < maze_w and 0 <= ny < maze_h:
                    if (nx, ny) not in visited:
                        real_x, real_y = cx * 2 + 1, cy * 2 + 1
                        target_x, target_y = nx * 2 + 1, ny * 2 + 1
                        mid_x, mid_y = real_x + dx, real_y + dy
                        self.tiles[(real_x, real_y)] = Tile(real_x, real_y, 'floor')
                        self.tiles[(target_x, target_y)] = Tile(target_x, target_y, 'floor')
                        self.tiles[(mid_x, mid_y)] = Tile(mid_x, mid_y, 'floor')
                        if (cx, cy) not in adjacency: adjacency[(cx, cy)] = []
                        if (nx, ny) not in adjacency: adjacency[(nx, ny)] = []
                        adjacency[(cx, cy)].append((nx, ny))
                        adjacency[(nx, ny)].append((cx, cy))
                        visited.add((nx, ny))
                        stack.append((nx, ny))
                        break
            else:
                stack.pop()
        #======
        self._place_walls()
        valid_floors = [k for k, v in self.tiles.items() if v.type == 'floor']
        valid_nodes = list(adjacency.keys())
        if valid_nodes:
            temp_start = random.choice(valid_nodes)
        else:
            temp_start = (0, 0)

        real_start = self._bfs_find_node(temp_start, adjacency)
        real_exit = self._bfs_find_node(real_start, adjacency)
        path = self._bfs_path(real_start, real_exit, adjacency)
        if not path: path = [real_start, real_exit]
        path_set = set(path)
        num_keys = random.randint(MAP_GEN['MIN_KEYS'], MAP_GEN['MAX_KEYS'])
        key_colors = [f'key_{i}' for i in range(num_keys)]
        segment_len = len(path) // (num_keys + 1)
        items = []
        #======
        for i in range(num_keys):
            door_node_idx = (i + 1) * segment_len
            if door_node_idx >= len(path): door_node_idx = len(path) - 1
            door_node = path[door_node_idx]
            dx, dy = door_node[0]*2 + 1, door_node[1]*2 + 1
            if (dx, dy) in self.tiles:
                self.tiles[(dx, dy)] = Tile(dx, dy, 'door')
                self.tiles[(dx, dy)].is_open = False
                self.tiles[(dx, dy)].locked = True
                self.tiles[(dx, dy)].key_color = key_colors[i]
            segment_start = i * segment_len
            segment_end = door_node_idx
            segment_nodes = path[segment_start:segment_end]
            random.shuffle(segment_nodes)
            found_key_pos = None
            for anchor_node in segment_nodes:
                branches = [n for n in adjacency.get(anchor_node, []) if n not in path_set]
                if branches:
                    start_branch = random.choice(branches)
                    forbidden_area = set(path_set)
                    forbidden_area.add(anchor_node)
                    found_key_pos = self._bfs_find_node(
                        start_branch, 
                        adjacency, 
                        forbidden=forbidden_area, 
                        shuffle=True, 
                        find_dead_end=True
                    )
                    break
            if not found_key_pos: found_key_pos = segment_nodes[0]
            kx, ky = found_key_pos[0]*2 + 1, found_key_pos[1]*2 + 1
            items.append({'pos': (kx, ky), 'name': f'Ключ {i+1}', 'color': key_colors[i]})
        #======
        player_start = (real_start[0]*2 + 1, real_start[1]*2 + 1)
        exit_pos = (real_exit[0]*2 + 1, real_exit[1]*2 + 1)
        enemies = []
        for _ in range(GAME_BALANCE['ENEMY_SPAWN_ATTEMPTS_MAZE']):
            ex, ey = random.randint(1, self.width-2), random.randint(1, self.height-2)
            if (ex, ey) in self.tiles and self.tiles[(ex, ey)].type == 'floor':
                enemies.append((ex, ey))
        return player_start, exit_pos, items, enemies
        #======

    def _bfs_find_node(self, start_node, adj, forbidden=None, shuffle=False, find_dead_end=False):
        queue = [start_node]
        visited = {start_node}
        if forbidden:
            visited.update(forbidden)
        last_node = start_node
        while queue:
            curr = queue.pop(0)
            last_node = curr
            if find_dead_end and len(adj.get(curr, [])) == 1:
                return curr
            neighbors = list(adj.get(curr, []))
            if shuffle:
                random.shuffle(neighbors)
            for nxt in neighbors:
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        
        return last_node

    def _tunnel_h(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2)+1): 
            self._dig(x, y)

    def _tunnel_v(self, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2)+1): 
            self._dig(x, y)

    def _set_tile_conditional(self, x, y, new_type, target_check='void'):
        if (x, y) not in self.tiles or self.tiles[(x, y)].type == target_check:
            self.tiles[(x, y)] = Tile(x, y, new_type)

    def _dig(self, x, y):
        self._set_tile_conditional(x, y, 'floor', 'void')

    def _place_walls(self):
        floor_tiles = [pos for pos, t in self.tiles.items() if t.type == 'floor']
        for x, y in floor_tiles:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = x+dx, y+dy
                    self._set_tile_conditional(nx, ny, 'wall', 'void')

    def _place_doors(self):
        for room in self.rooms:
            r = room.rect
            for x in range(r.left + 1, r.right - 1):
                self._try_set_door(x, r.top - 1, check_horizontal=True)
                self._try_set_door(x, r.bottom, check_horizontal=True)
            for y in range(r.top + 1, r.bottom - 1):
                self._try_set_door(r.left - 1, y, check_horizontal=False)
                self._try_set_door(r.right, y, check_horizontal=False)

    def _try_set_door(self, x, y, check_horizontal):
        if (x, y) not in self.tiles: return
        if self.tiles[(x, y)].type != 'floor': return
        left = self.tiles.get((x - 1, y))
        right = self.tiles.get((x + 1, y))
        top = self.tiles.get((x, y - 1))
        bot = self.tiles.get((x, y + 1))
        if check_horizontal:
            if left and left.type == 'wall' and right and right.type == 'wall':
                self.tiles[(x, y)] = Tile(x, y, 'door')
        else:
            if top and top.type == 'wall' and bot and bot.type == 'wall':
                self.tiles[(x, y)] = Tile(x, y, 'door')

    def _populate_standard_level(self, p_start, exit_pos):
        enemies, items, chests = [], [], []
        for room in self.rooms:
            if room.rect.collidepoint(p_start) or room.rect.collidepoint(exit_pos): continue
            if random.random() < GAME_BALANCE['ENEMY_CHANCE']:
                for _ in range(random.randint(1, GAME_BALANCE['MAX_ENEMIES_PER_ROOM'])):
                    ex, ey = self._rand_in_room(room)
                    enemies.append((ex, ey))
            if random.random() < GAME_BALANCE['GROUND_LOOT_CHANCE']:
                lx, ly = self._rand_in_room(room)
                items.append({'pos': (lx, ly), 'name': random.choice(LOOT_TABLE[min(3, 1+self.level//3)])})
            chest_count = 0
            if room.type == 'treasure': chest_count = 3
            elif random.random() < 0.3: chest_count = 1
            for _ in range(chest_count):
                cx, cy = self._rand_in_room(room)
                chests.append((cx, cy))
        return items, enemies, chests

    def _rand_in_room(self, room):
        return random.randint(room.rect.left+1, room.rect.right-2), random.randint(room.rect.top+1, room.rect.bottom-2)
    
    def _bfs_path(self, start, end, adj):
        queue = [(start, [start])]
        visited = {start}
        while queue:
            (vertex, path) = queue.pop(0)
            if vertex == end:
                return path
            for neighbor in adj.get(vertex, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return []