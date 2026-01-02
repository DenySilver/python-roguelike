import pygame, sys
from settings import *
from map_generator import MapGenerator
from entities import Player, Enemy, Item, Chest
from utils import Camera, compute_fov
from spritesheet import SpriteSheet

class Log:
    def __init__(self):
        self.messages = []
    def add(self, msg):
        self.messages.append(msg)
        if len(self.messages) > 6: self.messages.pop(0)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", UI_SETTINGS['FONT_SIZE'])
        self.big_font = pygame.font.SysFont("Arial", UI_SETTINGS['BIG_FONT_SIZE'], bold=True)
        self.debug_font = pygame.font.SysFont("Arial", UI_SETTINGS['DEBUG_FONT_SIZE'], bold=True)
        self.spritesheet = SpriteSheet("assets/sprites.png")
        self.assets = self._load_sprites()
        self.log = Log()
        self.current_level = 1
        self.camera = Camera(WIDTH, HEIGHT)
        self.floating_texts = []
        self.show_inventory = False
        self.debug_mode = False
        self.stats = {'kills': 0, 'moves': 0, 'level_max_reached': 1}
        self.saved_levels = {}
        self.new_game(reset_player=True)

    def _load_sprites(self):
        assets = {}
        for name, rect in SPRITES.items():
            color = None
            if 'enemy' in name: color = COLORS['RED']
            assets[name] = self.spritesheet.get_sprite(rect[0], rect[1], rect[2], rect[3], color)
        return assets

    def save_level_state(self):
        if not hasattr(self, 'map_data'): return
        self.saved_levels[self.current_level] = {
            'map_data': self.map_data,
            'enemies': self.enemies,
            'items': self.items,
            'chests': self.chests,
            'rooms': self.rooms,
            'exit_pos': self.exit_pos,
            'player_start': self.level_start_pos,
            'explored': True
        }

    def load_level_state(self, level_num):
        data = self.saved_levels[level_num]
        self.map_data = data['map_data']
        self.enemies = data['enemies']
        self.items = data['items']
        self.chests = data['chests']
        self.rooms = data['rooms']
        self.exit_pos = data['exit_pos']
        self.level_start_pos = data['player_start']
        for e in self.enemies: e.game = self
        for i in self.items: i.game = self
        for c in self.chests: c.game = self

    def new_game(self, reset_player=False, going_up=False, save_old=True):
        if not reset_player and save_old:
            self.save_level_state()
        if reset_player:
            self.saved_levels = {}
            self.current_level = 1
            self.stats = {'kills': 0, 'moves': 0, 'level_max_reached': 1}
        self.log.add(f"--- Рівень {self.current_level} ---")
        if self.current_level in self.saved_levels:
            print(f"[Game] ЗАВАНТАЖЕННЯ рівня {self.current_level} зі збереження")
            self.load_level_state(self.current_level)
            p_start = self.level_start_pos
        else:
            print(f"[Game] ГЕНЕРАЦІЯ нового рівня {self.current_level}...")
            gen = MapGenerator(self.current_level)
            self.map_data, p_start, self.exit_pos, enemies_pos, items_data, chests_pos = gen.generate()
            self.rooms = gen.rooms
            self.level_start_pos = p_start
            self.enemies = []
            for (ex, ey) in enemies_pos:
                self.enemies.append(Enemy(ex, ey, self.current_level, self))
            self.items = []
            for i_data in items_data:
                self.items.append(Item(i_data['pos'][0], i_data['pos'][1], i_data['name'], self, i_data.get('color')))
            self.chests = []
            for (cx, cy) in chests_pos:
                self.chests.append(Chest(cx, cy, self))
        if reset_player or not hasattr(self, 'player'):
            self.player = Player(p_start[0], p_start[1], self)
        else:
            self.player.game = self
            if going_up:
                self.player.x, self.player.y = self.exit_pos
            else:
                self.player.x, self.player.y = self.level_start_pos
        if self.current_level > self.stats['level_max_reached']:
            self.stats['level_max_reached'] = self.current_level
        self.camera.center_on(self.player.x, self.player.y)
        self.update_fov()

    def update_fov(self):
        visible = compute_fov(self.player.x, self.player.y, FOV_RADIUS, self.map_data)
        for pos in visible:
            self.map_data[pos].visible = True
            self.map_data[pos].explored = True
        for pos, tile in self.map_data.items():
            if pos not in visible: tile.visible = False

    def get_enemy_at(self, x, y):
        for e in self.enemies:
            if e.x == x and e.y == y: return e
        return None

    def get_chest_at(self, x, y):
        for c in self.chests:
            if c.x == x and c.y == y: return c
        return None

    def is_blocked(self, x, y):
        if (x, y) not in self.map_data: return True
        if self.map_data[(x, y)].blocked: return True
        if self.get_enemy_at(x, y): return True
        if self.get_chest_at(x, y) and not self.get_chest_at(x, y).is_open: return True
        if (self.player.x, self.player.y) == (x, y): return True
        return False

    def add_floating_text(self, text, x, y, color):
        self.floating_texts.append({'text': text, 'x': x, 'y': y, 'timer': 60, 'color': color, 'offset_y': 0.0})

    def show_victory_screen(self):
        waiting = True
        while waiting:
            self.screen.fill(COLORS['BLACK'])
            title = self.big_font.render("ВИ ПЕРЕМОГЛИ!", True, COLORS['YELLOW'])
            msg1 = self.font.render("Ви винесли Амулет Єндора з підземелля!", True, COLORS['WHITE'])
            stats_txt = [
                f"Вбито ворогів: {self.stats['kills']}",
                f"Зроблено ходів: {self.stats['moves']}",
                f"Макс. глибина: {self.stats['level_max_reached']}"
            ]
            exit_msg = self.font.render("Натисніть будь-яку клавішу для виходу...", True, COLORS['UI_TEXT_DIM'])
            cw, ch = WIDTH // 2, HEIGHT // 2
            self.screen.blit(title, title.get_rect(center=(cw, ch - 100)))
            self.screen.blit(msg1, msg1.get_rect(center=(cw, ch - 50)))
            y_off = 0
            for line in stats_txt:
                s = self.font.render(line, True, COLORS['WHITE'])
                self.screen.blit(s, s.get_rect(center=(cw, ch + y_off)))
                y_off += 30
            self.screen.blit(exit_msg, exit_msg.get_rect(center=(cw, HEIGHT - 50)))
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN: pygame.quit(); sys.exit()

    def draw_inventory(self):
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        s.fill(COLORS['PANEL_BG'])
        self.screen.blit(s, (0, 0))
        rect_dims = UI_SETTINGS['INVENTORY_RECT']
        rect = pygame.Rect(rect_dims)
        pygame.draw.rect(self.screen, COLORS['BG_DEFAULT'], rect)
        pygame.draw.rect(self.screen, COLORS['BORDER'], rect, 3)
        title = "ІНВЕНТАР (1-9: Вик., Shift+1-9: Викинути, I: Закр.)"
        self.screen.blit(self.font.render(title, True, COLORS['WHITE']), (rect.x+20, rect.y+20))
        min_d, max_d = self.player.damage_range
        stats = f"Атака: {min_d}-{max_d} | Захист: {self.player.defense}"
        self.screen.blit(self.font.render(stats, True, COLORS['YELLOW']), (rect.x+20, rect.y+50))
        y_off = 90
        for i, item_name in enumerate(self.player.inventory):
            desc = ITEMS_DB[item_name]['desc']
            color = COLORS['YELLOW'] if item_name == WIN_ITEM else COLORS['WHITE']
            txt = f"{i+1}. {item_name} ({desc})"
            self.screen.blit(self.font.render(txt, True, color), (rect.x+30, rect.y+y_off))
            y_off += 25

    def draw(self):
        biome = BIOMES.get((self.current_level-1)//LEVELS_PER_BIOME, BIOMES[0])
        self.screen.fill(biome['bg'])
        occupied_cells = set()
        occupied_cells.add((self.player.x, self.player.y))
        for e in self.enemies: occupied_cells.add((e.x, e.y))
        for i in self.items: occupied_cells.add((i.x, i.y))

        for (x, y), tile in self.map_data.items():
            if not tile.explored and not self.debug_mode: continue
            rect = pygame.Rect(x*TILE_SIZE, y*TILE_SIZE, TILE_SIZE, TILE_SIZE)
            screen_rect = self.camera.apply_rect(rect)
            if screen_rect.right < 0 or screen_rect.left > WIDTH or screen_rect.bottom < 0 or screen_rect.top > HEIGHT:
                continue
            if tile.type in ['floor', 'door', 'stairs_down', 'stairs_up']:
                key = 'floor'
                if tile.variant == 1: key = 'floor_dec_1'
                elif tile.variant == 2: key = 'floor_dec_2'
                img = self.assets[key].copy()
                img.fill(biome['floor_tint'], special_flags=pygame.BLEND_RGBA_MULT)
                scaled = pygame.transform.scale(img, (screen_rect.width, screen_rect.height))
                self.screen.blit(scaled, screen_rect)
            img = None
            if tile.type == 'wall':
                wall_keys = ['wall_1', 'wall_2', 'wall_3']
                key = wall_keys[tile.variant % 3]
                img = self.assets[key].copy()
                img.fill(biome['wall_tint'], special_flags=pygame.BLEND_RGBA_MULT)
            elif tile.type == 'door':
                if (x, y) not in occupied_cells:
                    img = self.assets['door_open' if tile.is_open else 'door_closed']
            elif tile.type == 'stairs_down':
                if (x, y) != (self.player.x, self.player.y): img = self.assets['stairs_down']
            elif tile.type == 'stairs_up':
                if (x, y) != (self.player.x, self.player.y): img = self.assets['stairs_up']
            if img:
                scaled = pygame.transform.scale(img, (screen_rect.width, screen_rect.height))
                self.screen.blit(scaled, screen_rect)
            if not tile.visible and not self.debug_mode:
                s = pygame.Surface((screen_rect.width, screen_rect.height), pygame.SRCALPHA)
                s.fill((0, 0, 0, 150))
                self.screen.blit(s, screen_rect)

        for chest in self.chests:
            if self.map_data[(chest.x, chest.y)].visible or self.debug_mode:
                if (chest.x, chest.y) not in occupied_cells:
                    r = pygame.Rect(chest.x*TILE_SIZE, chest.y*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    sr = self.camera.apply_rect(r)
                    key = 'chest_open' if chest.is_open else 'chest'
                    img = self.assets.get(key, self.assets['chest'])
                    scaled = pygame.transform.scale(img, (sr.width, sr.height))
                    self.screen.blit(scaled, sr)

        for item in self.items:
            if self.map_data[(item.x, item.y)].visible or self.debug_mode:
                if item.data['type'] == 'artifact':
                    rect = pygame.Rect(item.x * TILE_SIZE, item.y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    sr = self.camera.apply_rect(rect)
                    scaled = pygame.transform.scale(self.assets['artifact'], (sr.width, sr.height))
                    self.screen.blit(scaled, sr)
                else:
                    item.draw(self.screen, self.camera, self.assets)

        for enemy in self.enemies:
            if self.map_data[(enemy.x, enemy.y)].visible or self.debug_mode:
                r = pygame.Rect(enemy.x*TILE_SIZE, enemy.y*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                sr = self.camera.apply_rect(r)
                scaled = pygame.transform.scale(self.assets[enemy.sprite_key], (sr.width, sr.height))
                self.screen.blit(scaled, sr)
                bar_w = sr.width
                hp_pct = max(0, enemy.hp / enemy.max_hp)
                pygame.draw.rect(self.screen, COLORS['RED'], (sr.x, sr.y - 5, bar_w * hp_pct, 4))
                if self.debug_mode:
                    path_len = len(enemy.path) if enemy.path else 0
                    debug_txt = f"{enemy.state} ({path_len})"
                    txt_surf = self.debug_font.render(debug_txt, True, COLORS['WHITE'])
                    txt_x = sr.centerx - txt_surf.get_width() // 2
                    txt_y = sr.top - 20
                    bg_rect = pygame.Rect(txt_x - 2, txt_y - 2, txt_surf.get_width() + 4, txt_surf.get_height() + 4)
                    pygame.draw.rect(self.screen, COLORS['DEBUG_BG'], bg_rect)
                    self.screen.blit(txt_surf, (txt_x, txt_y))

        pr = pygame.Rect(self.player.x*TILE_SIZE, self.player.y*TILE_SIZE, TILE_SIZE, TILE_SIZE)
        spr = self.camera.apply_rect(pr)
        sprite_key = 'grave' if self.player.is_dead else 'player'
        scaled_p = pygame.transform.scale(self.assets[sprite_key], (spr.width, spr.height))
        self.screen.blit(scaled_p, spr)

        for ft in self.floating_texts[:]:
            ft['timer'] -= 1
            ft['offset_y'] -= 0.5
            if ft['timer'] <= 0: self.floating_texts.remove(ft)
            else:
                r = pygame.Rect(ft['x']*TILE_SIZE, ft['y']*TILE_SIZE, 0, 0)
                sr = self.camera.apply_rect(r)
                screen_x = sr.x + (TILE_SIZE * self.camera.zoom // 2)
                screen_y = sr.y + ft['offset_y']
                txt_surf = self.font.render(ft['text'], True, ft['color'])
                txt_rect = txt_surf.get_rect(center=(screen_x, screen_y))
                self.screen.blit(txt_surf, txt_rect)

        if self.show_inventory:
            self.draw_inventory()
        else:
            info = f"HP: {self.player.hp}/{self.player.max_hp} | Глибина: {self.current_level}/{MAX_LEVEL}"
            self.screen.blit(self.font.render(info, True, COLORS['WHITE']), (10, 10))
            help_txt = "[I] Інвентар | [Пробіл] Чекати | [Enter] Сходи"
            if self.current_level == 1 and WIN_ITEM in self.player.inventory:
                help_txt = "[ENTER] ЩОБ ВИЙТИ І ПЕРЕМОГТИ!"
            self.screen.blit(self.font.render(help_txt, True, COLORS['YELLOW']), (10, 30))
            y = HEIGHT - 20
            for msg in reversed(self.log.messages):
                self.screen.blit(self.font.render(msg, True, COLORS['UI_TEXT_DIM']), (10, y))
                y -= 20

        if self.debug_mode:
            for e in self.enemies:
                if hasattr(e, 'path') and e.path:
                    start_rect = pygame.Rect(e.x * TILE_SIZE, e.y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    start_scr = self.camera.apply_rect(start_rect).center
                    points = [start_scr]
                    for step in e.path:
                        r = pygame.Rect(step[0] * TILE_SIZE, step[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                        scr_pos = self.camera.apply_rect(r).center
                        points.append(scr_pos)
                    if len(points) > 1:
                        pygame.draw.lines(self.screen, COLORS['RED'], False, points, 2)
                        pygame.draw.circle(self.screen, COLORS['GREEN'], points[-1], 4)
        if self.player.is_dead:
            self.draw_game_over()
        pygame.display.flip()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                self.camera.handle_event(event)
                if event.type == pygame.KEYDOWN:
                    if self.player.is_dead:
                        if event.key == pygame.K_r:
                            self.new_game(reset_player=True)
                        continue
                    if event.key == pygame.K_F1:
                        self.debug_mode = not self.debug_mode
                        self.log.add(f"Debug Mode: {self.debug_mode}")
                        if self.debug_mode:
                            if WIN_ITEM not in self.player.inventory:
                                self.player.inventory.append(WIN_ITEM)
                                self.log.add("DEBUG: Отримано Амулет!")
                    if event.key == pygame.K_i:
                        self.show_inventory = not self.show_inventory
                    if self.show_inventory:
                        if pygame.K_1 <= event.key <= pygame.K_9:
                            idx = event.key - pygame.K_1
                            mods = pygame.key.get_mods()
                            if mods & pygame.KMOD_SHIFT:
                                self.player.drop_item(idx)
                            else:
                                self.player.use_item(idx)
                    else:
                        dx, dy = 0, 0
                        turn_taken = False
                        if event.key == pygame.K_LEFT: dx = -1
                        elif event.key == pygame.K_RIGHT: dx = 1
                        elif event.key == pygame.K_UP: dy = -1
                        elif event.key == pygame.K_DOWN: dy = 1
                        elif event.key == pygame.K_SPACE:
                            turn_taken = self.player.wait()
                        elif event.key == pygame.K_RETURN:
                            px, py = self.player.x, self.player.y
                            tile = self.map_data.get((px, py))
                            if tile:
                                if tile.type == 'stairs_down':
                                    self.save_level_state()
                                    self.current_level += 1
                                    self.log.add("Ви спустилися глибше...")
                                    self.new_game(going_up=False, save_old=False)
                                elif tile.type == 'stairs_up':
                                    if self.current_level == 1:
                                        if WIN_ITEM in self.player.inventory:
                                            self.show_victory_screen()
                                        else:
                                            self.log.add("Ви не можете піти без Артефакту!")
                                    else:
                                        self.save_level_state()
                                        self.current_level -= 1
                                        self.log.add("Ви піднялися вище...")
                                        self.new_game(going_up=True, save_old=False)
                                else:
                                    self.log.add("Тут немає сходів.")
                        if dx!=0 or dy!=0:
                            turn_taken = self.player.move(dx, dy)
                            if turn_taken:
                                self.stats['moves'] += 1
                                self.camera.center_on(self.player.x, self.player.y)
                        if turn_taken:
                            self.update_fov()
                            for e in self.enemies: e.take_turn()
            self.camera.update()
            self.draw()
            self.clock.tick(FPS)

    def draw_game_over(self):
        panel_w, panel_h = UI_SETTINGS['GAME_OVER_PANEL']
        s = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        s.fill(COLORS['PANEL_BG'])
        pygame.draw.rect(s, COLORS['GAME_OVER_BORDER'], (0, 0, panel_w, panel_h), 2)
        title = self.big_font.render("R.I.P.", True, COLORS['GAME_OVER_TEXT'])
        sub_title = self.font.render("Ви загинули...", True, COLORS['UI_TEXT_DIM'])
        stats_lines = [
            f"Глибина: {self.current_level} (Макс: {self.stats['level_max_reached']})",
            f"Вбито ворогів: {self.stats['kills']}",
            f"Кроків: {self.stats['moves']}",
        ]
        cx = panel_w // 2
        s.blit(title, title.get_rect(center=(cx, 40)))
        s.blit(sub_title, sub_title.get_rect(center=(cx, 80)))
        y_off = 120
        for line in stats_lines:
            txt = self.font.render(line, True, COLORS['WHITE'])
            s.blit(txt, txt.get_rect(center=(cx, y_off)))
            y_off += 25
        hint = self.font.render("[R] Рестарт", True, COLORS['YELLOW'])
        s.blit(hint, hint.get_rect(center=(cx, panel_h - 30)))
        screen_x = WIDTH - panel_w - UI_SETTINGS['OFFSET_X']
        screen_y = HEIGHT // 2 - panel_h // 2
        self.screen.blit(s, (screen_x, screen_y))

if __name__ == "__main__":
    Game().run()