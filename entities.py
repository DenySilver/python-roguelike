import pygame
import random
from settings import *
from utils import get_path, has_line_of_sight

class Entity:
    def __init__(self, x, y, name, game):
        self.x = x
        self.y = y
        self.name = name
        self.game = game

class Item(Entity):
    def __init__(self, x, y, item_key, game, color=None):
        super().__init__(x, y, item_key, game)
        if "Ключ" in item_key:
            self.data = ITEMS_DB['Ключ']
        else:
            self.data = ITEMS_DB[item_key]
        self.type = self.data['type']
        self.color_tint = color

    def draw(self, screen, camera, assets):
        sprite_key = 'loot_potion'
        if self.type == 'weapon': sprite_key = 'loot_weapon'
        elif self.type == 'armor': sprite_key = 'loot_armor'
        elif self.type == 'key': sprite_key = 'key'
        img = assets[sprite_key].copy()
        if self.color_tint:
            colors = {
                'key_0': (205, 127, 50),
                'key_1': (192, 192, 192),
                'key_2': (255, 215, 0),
                'key_3': (0, 255, 255),
                'key_4': (255, 0, 255)
            }
            rgb = colors.get(self.color_tint, COLORS['WHITE'])
            colored_surface = pygame.Surface(img.get_size()).convert_alpha()
            colored_surface.fill(rgb)
            img.blit(colored_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        rect = pygame.Rect(self.x * TILE_SIZE, self.y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        screen_rect = camera.apply_rect(rect)
        if screen_rect.width > 0:
            scaled_img = pygame.transform.scale(img, (int(screen_rect.width), int(screen_rect.height)))
            screen.blit(scaled_img, screen_rect)

class Player(Entity):
    def __init__(self, x, y, game):
        super().__init__(x, y, "Герой", game)
        self.hp = 100
        self.max_hp = 100
        self.base_damage = 5
        self.base_defense = 0
        self.inventory = []
        self.equipment = {'weapon': None, 'armor': None}

    @property
    def damage_range(self):
        bonus = ITEMS_DB[self.equipment['weapon']]['val'] if self.equipment['weapon'] else 0
        base = self.base_damage + bonus
        return (int(base * 0.8), int(base * 1.2))

    @property
    def defense(self):
        bonus = ITEMS_DB[self.equipment['armor']]['val'] if self.equipment['armor'] else 0
        return self.base_defense + bonus

    def roll_damage(self):
        min_d, max_d = self.damage_range
        return random.randint(min_d, max_d)

    @property
    def is_dead(self):
        return self.hp <= 0

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp < 0: self.hp = 0
        self.game.add_floating_text(f"-{amount}", self.x, self.y, COLORS['RED'])
        if self.is_dead:
            self.game.log.add("ВИ ЗАГИНУЛИ!")

    def move(self, dx, dy):
        target_x = self.x + dx
        target_y = self.y + dy
        if (target_x, target_y) in self.game.map_data:
            tile = self.game.map_data[(target_x, target_y)]
            if tile.type == 'door' and tile.blocked:
                if tile.locked:
                    key_idx = -1
                    for i, item in enumerate(self.inventory):
                        if "Ключ" in item:
                            key_idx = i
                            break
                    if key_idx != -1:
                        self.game.log.add("Ви відімкнули двері ключем!")
                        self.inventory.pop(key_idx)
                        tile.locked = False
                        tile.blocked = False
                        tile.block_sight = False
                        tile.is_open = True
                        return True
                    else:
                        self.game.log.add("Двері заперті! Потрібен ключ.")
                        return True
                else:
                    tile.blocked = False
                    tile.block_sight = False
                    tile.is_open = True
                    self.game.log.add("Ви відкрили двері.")
                    return True
            chest = self.game.get_chest_at(target_x, target_y)
            if chest and not chest.is_open:
                chest.interact()
                return True
            if not tile.blocked:
                enemy = self.game.get_enemy_at(target_x, target_y)
                if enemy:
                    self.attack(enemy)
                    return True
                self.x, self.y = target_x, target_y
                for item in self.game.items[:]:
                    if item.x == self.x and item.y == self.y:
                        self.game.log.add(f"Підібрано: {item.name}")
                        self.inventory.append(item.name)
                        self.game.items.remove(item)
                return True
        return False

    def attack(self, target):
        dmg = self.roll_damage()
        actual_dmg = max(1, dmg - target.defense)
        target.take_damage(actual_dmg)
        self.game.add_floating_text(f"-{actual_dmg}", target.x, target.y, COLORS['WHITE'])

    def wait(self):
        self.game.log.add("Ви чекаєте...")
        return True

    def use_item(self, index):
        if 0 <= index < len(self.inventory):
            item_name = self.inventory[index]
            data = ITEMS_DB[item_name]
            if data['type'] == 'potion':
                heal = data['val']
                self.hp = min(self.max_hp, self.hp + heal)
                self.game.log.add(f"Ви випили {item_name} (+{heal} HP)")
                self.inventory.pop(index)
            elif data['type'] in ['weapon', 'armor']:
                slot = data['type']
                if self.equipment[slot]:
                    self.inventory.append(self.equipment[slot])
                self.equipment[slot] = item_name
                self.inventory.pop(index)
                self.game.log.add(f"Екіпіровано: {item_name}")

    def drop_item(self, index):
        if 0 <= index < len(self.inventory):
            item_name = self.inventory.pop(index)
            dropped_item = Item(self.x, self.y, item_name, self.game)
            self.game.items.append(dropped_item)
            self.game.log.add(f"Ви викинули: {item_name}")
            return True
        return False

class Chest(Entity):
    def __init__(self, x, y, game):
        super().__init__(x, y, "Скриня", game)
        self.is_open = False
        self.is_mimic = random.random() < GAME_BALANCE['MIMIC_CHANCE']

    def interact(self):
        if self.is_open: return False
        if self.is_mimic:
            self.game.log.add("Це пастка! Скриня оживає!")
            if self in self.game.chests: self.game.chests.remove(self)
            mimic = Enemy(self.x, self.y, self.game.current_level, self.game, force_type='mimic')
            self.game.enemies.append(mimic)
            return True
        self.is_open = True
        tier = min(3, 1 + self.game.current_level // 3)
        for _ in range(random.randint(1, 2)):
            item_name = random.choice(LOOT_TABLE[tier])
            self.game.items.append(Item(self.x, self.y, item_name, self.game))
        self.game.log.add("Скриня відкрита.")
        return True

class Enemy(Entity):
    def __init__(self, x, y, level, game, force_type=None):
        if force_type:
            enemy_type_id = force_type
        else:
            available_types = ['rat']
            for min_lvl, enemies_list in ENEMY_SPAWN_RULES:
                if level >= min_lvl: available_types = enemies_list
                else: break
            enemy_type_id = random.choice(available_types)
        stats = ENEMIES_DB[enemy_type_id]
        self.type_id = enemy_type_id
        super().__init__(x, y, stats['name'], game)
        self.sprite_key = stats['sprite']
        hp_mult = 1.0 + (level * 0.2)
        dmg_mult = 1.0 + (level * 0.1)
        self.max_hp = int(stats['base_hp'] * hp_mult)
        self.hp = self.max_hp
        self.base_damage = int(stats['base_dmg'] * dmg_mult)
        self.defense = level // 3
        self.moves_per_turn = stats['moves']
        self.attacks_per_turn = stats['attacks']
        self.vision_radius = stats['vision']
        self.move_energy = 0.0
        self.attack_energy = 0.0
        if random.random() < stats['patrol_chance']:
            self.state = 'patrol'
        else:
            self.state = 'sleep'
        self.last_seen_pos = None
        self.path = []
        self.patrol_target = None
        self.stuck_counter = 0

    def take_turn(self):
        player = self.game.player
        dist = ((self.x - player.x)**2 + (self.y - player.y)**2)**0.5
        can_see = False
        if dist <= self.vision_radius:
            if has_line_of_sight(self.x, self.y, player.x, player.y, self.game.map_data):
                can_see = True
        if can_see:
            if self.state == 'sleep':
                self.game.log.add(f"{self.name} прокинувся!")
            self.state = 'chase'
            self.last_seen_pos = (player.x, player.y)
            if self.path and self.path[-1] != (player.x, player.y):
                self.path = []
        elif self.state == 'chase' and not can_see:
            self.state = 'hunt'
            self.game.add_floating_text("?", self.x, self.y, COLORS['YELLOW'])
        if self.state == 'sleep':
            return
        self.move_energy += self.moves_per_turn
        self.attack_energy += self.attacks_per_turn
        if self.state == 'chase':
            if dist < 1.5:
                while self.attack_energy >= 1.0:
                    self.attack(player)
                    self.attack_energy -= 1.0
                self.move_energy = 0
            else:
                while self.move_energy >= 1.0:
                    self._move_via_path((player.x, player.y))
                    self.move_energy -= 1.0
                    new_dist = ((self.x - player.x)**2 + (self.y - player.y)**2)**0.5
                    if new_dist < 1.5:
                        break
        elif self.state == 'hunt':
            while self.move_energy >= 1.0:
                self._hunt_logic()
                self.move_energy -= 1.0
        elif self.state == 'patrol':
            while self.move_energy >= 1.0:
                self._patrol_logic()
                self.move_energy -= 1.0

    def _hunt_logic(self):
        if not self.last_seen_pos:
            self.state = 'patrol'
            return
        if (self.x, self.y) == self.last_seen_pos:
            self.state = 'patrol'
            self.patrol_target = None
            self.game.add_floating_text("...", self.x, self.y, COLORS['UI_TEXT_DIM'])
        else:
            self._move_via_path(self.last_seen_pos)

    def _patrol_logic(self):
        if not self.patrol_target or (self.x, self.y) == self.patrol_target:
            self.path = []
            self.patrol_target = None
            targets = []
            if hasattr(self.game, 'rooms') and self.game.rooms:
                valid_rooms = [r for r in self.game.rooms if r.type != 'start']
                if valid_rooms:
                    targets = [r.center for r in valid_rooms]
            if not targets:
                floors = [pos for pos, tile in self.game.map_data.items() if tile.type == 'floor']
                if floors:
                    targets = random.sample(floors, min(len(floors), 10))
            if targets:
                random.shuffle(targets)
                obstacles = set()
                for e in self.game.enemies:
                    if e != self: obstacles.add((e.x, e.y))
                for c in self.game.chests:
                    if not c.is_open: obstacles.add((c.x, c.y))
                for t in targets:
                    if self.game.get_enemy_at(t[0], t[1]): continue
                    chest = self.game.get_chest_at(t[0], t[1])
                    if chest and not chest.is_open: continue
                    test_path = get_path((self.x, self.y), t, self.game.map_data, obstacles)
                    if test_path:
                        self.patrol_target = t
                        self.path = test_path
                        self.stuck_counter = 0
                        break
            if not self.patrol_target:
                self.state = 'sleep'
        if self.patrol_target:
            self._move_via_path(self.patrol_target)

    def _move_via_path(self, target_pos):
        if not self.path or self.path[-1] != target_pos:
            obstacles = set()
            for e in self.game.enemies:
                if e != self:
                    obstacles.add((e.x, e.y))
            for c in self.game.chests:
                if not c.is_open:
                    obstacles.add((c.x, c.y))
            self.path = get_path((self.x, self.y), target_pos, self.game.map_data, obstacles)
            self.stuck_counter = 0
            if not self.path and (self.x, self.y) != target_pos:
                self.patrol_target = None
                return
        if self.path:
            next_step = self.path[0]
            nx, ny = next_step
            if (nx, ny) == (self.game.player.x, self.game.player.y):
                self.state = 'chase'
                self.attack(self.game.player)
                self.path = []
                return
            if self.game.get_enemy_at(nx, ny):
                self.stuck_counter += 1
                if self.stuck_counter > 1:
                    self.path = []
                    self.stuck_counter = 0
                return
            chest = self.game.get_chest_at(nx, ny)
            if chest and not chest.is_open:
                self.path = []
                return
            dx = nx - self.x
            dy = ny - self.y
            if self._try_move(dx, dy):
                self.path.pop(0)
                self.stuck_counter = 0
            else:
                self.path = []

    def _try_move(self, dx, dy):
        tx, ty = self.x + dx, self.y + dy
        if (tx, ty) not in self.game.map_data:
            return False
        tile = self.game.map_data[(tx, ty)]
        if tile.type == 'door' and not tile.is_open:
            if not tile.locked:
                tile.is_open = True
                tile.blocked = False
                tile.block_sight = False
                return True
            else:
                return False
        if not self.game.is_blocked(tx, ty):
            self.x = tx
            self.y = ty
            return True
        return False

    def attack(self, target):
        dmg = random.randint(int(self.base_damage * 0.8), int(self.base_damage * 1.2))
        actual = max(0, dmg - target.defense)
        target.take_damage(actual)
        self.game.log.add(f"{self.name} б'є вас на {actual}!")

    def take_damage(self, amount):
        self.hp -= amount
        if self.state == 'sleep':
            self.state = 'chase'
            self.last_seen_pos = (self.game.player.x, self.game.player.y)
        if self.hp <= 0:
            self.game.log.add(f"{self.name} вмирає.")
            if self in self.game.enemies:
                self.game.enemies.remove(self)
            is_mimic = (self.type_id == 'mimic')
            if is_mimic or random.random() < 0.3:
                base_tier = min(3, 1 + self.game.current_level // 3)
                final_tier = min(3, base_tier + 1) if is_mimic else base_tier
                item_name = random.choice(LOOT_TABLE[final_tier])
                self.game.items.append(Item(self.x, self.y, item_name, self.game))