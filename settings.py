import pygame

WIDTH, HEIGHT = 800, 600
FPS = 60
TITLE = "Roguelike RPG"

TILE_SIZE = 32
FOV_RADIUS = 10
MIN_ZOOM = 0.5
MAX_ZOOM = 2.0

COLORS = {
    'BG_DEFAULT': (20, 24, 46),
    'WHITE': (255, 255, 255),
    'RED': (255, 50, 50),
    'GREEN': (50, 255, 50),
    'YELLOW': (255, 215, 0),
    'BLACK': (0, 0, 0),
    'PANEL_BG': (0, 0, 0, 200),
    'BORDER': (200, 200, 200),
    'GAME_OVER_BORDER': (150, 0, 0),
    'GAME_OVER_TEXT': (200, 0, 0),
    'UI_TEXT_DIM': (200, 200, 200),
    'DEBUG_BG': (0, 0, 0, 180)
}

UI_SETTINGS = {
    'FONT_SIZE': 16,
    'BIG_FONT_SIZE': 48,
    'DEBUG_FONT_SIZE': 12,
    'GAME_OVER_PANEL': (250, 300),
    'INVENTORY_RECT': (100, 100, WIDTH - 200, HEIGHT - 200),
    'OFFSET_X': 50
}

MAP_GEN = {
    'SECT_WIDTH': 10,
    'SECT_HEIGHT': 10,
    'EXTRA_CONNECTIONS_FACTOR': 0.3,
    'TREASURE_ROOM_CHANCE': 0.15,
    'TUNNEL_RANDOMNESS': 0.5,
    'MIN_ROOM_SIZE': 4,
    'MAX_KEYS': 5,
    'MIN_KEYS': 3
}

BIOMES = {
    0: {'bg': (20, 24, 46), 'wall_tint': (150, 150, 200), 'floor_tint': (40, 45, 70)},
}

LEVELS_PER_BIOME = 5
MAX_LEVEL = len(BIOMES) * LEVELS_PER_BIOME
WIN_ITEM = "Амулет Єндора"

GAME_BALANCE = {
    'GROUND_LOOT_CHANCE': 0.2,
    'ENEMY_CHANCE': 0.15,
    'MAX_ENEMIES_PER_ROOM': 2,
    'MIMIC_CHANCE': 0.1,
    'ENEMY_SPAWN_ATTEMPTS_MAZE': 10
}

LOOT_TABLE = {
    1: ['Іржавий меч', 'Тряпічна куртка', 'Мале зілля'],
    2: ['Сталевий меч', 'Кожана броня', 'Зілля лікування'],
    3: ['Міфріловий клинок', 'Лати', 'Велике зілля']
}

ITEMS_DB = {
    'Іржавий меч': {'type': 'weapon', 'val': 2, 'desc': '+2 Атаки'},
    'Сталевий меч': {'type': 'weapon', 'val': 5, 'desc': '+5 Атаки'},
    'Міфріловий клинок': {'type': 'weapon', 'val': 10, 'desc': '+10 Атаки'},
    'Тряпічна куртка': {'type': 'armor', 'val': 1, 'desc': '+1 Захисту'},
    'Кожана броня': {'type': 'armor', 'val': 3, 'desc': '+3 Захисту'},
    'Лати': {'type': 'armor', 'val': 6, 'desc': '+6 Захисту'},
    'Мале зілля': {'type': 'potion', 'val': 20, 'desc': 'Лікування 20'},
    'Зілля лікування': {'type': 'potion', 'val': 50, 'desc': 'Лікування 50'},
    'Велике зілля': {'type': 'potion', 'val': 100, 'desc': 'Лікування 100'},
    'Ключ': {'type': 'key', 'val': 0, 'desc': 'Відчиняє заперті двері'},
    WIN_ITEM: {'type': 'artifact', 'val': 0, 'desc': 'Поверніть це на 1 поверх!'}
}

ENEMIES_DB = {
    'rat': {'name': 'Щур', 'sprite': 'enemy_rat', 'base_hp': 10, 'base_dmg': 3, 'moves': 2, 'attacks': 1, 'vision': 8, 'patrol_chance': 0.3},
    'goblin': {'name': 'Гоблін', 'sprite': 'enemy_goblin', 'base_hp': 20, 'base_dmg': 6, 'moves': 1, 'attacks': 1, 'vision': 9, 'patrol_chance': 0.5},
    'berserk': {'name': 'Гоблін-Берсерк', 'sprite': 'enemy_goblin', 'base_hp': 15, 'base_dmg': 4, 'moves': 1, 'attacks': 2, 'vision': 10, 'patrol_chance': 1.0},
    'skeleton': {'name': 'Скелет', 'sprite': 'enemy_skel', 'base_hp': 40, 'base_dmg': 10, 'moves': 2, 'attacks': 1, 'vision': 10, 'patrol_chance': 1.0},
    'mimic': {'name': 'Мімік', 'sprite': 'mimic', 'base_hp': 30, 'base_dmg': 8, 'moves': 1, 'attacks': 1, 'vision': 10, 'patrol_chance': 0.0}
}

ENEMY_SPAWN_RULES = [
    (1, ['rat']),
    (3, ['rat', 'goblin']),
    (5, ['goblin', 'berserk']),
    (7, ['goblin', 'skeleton']),
    (10, ['skeleton', 'berserk'])
]

SPRITES = {
    'floor': (32, 195, 16, 16),
    'floor_dec_1': (50, 547, 16, 16),
    'floor_dec_2': (34, 547, 16, 16),
    'wall_1': (32, 416, 16, 16),
    'wall_2': (48, 416, 16, 16),
    'wall_3': (64, 416, 16, 16),
    'door_closed': (225, 417, 16, 16),
    'door_open': (241, 417, 16, 16),
    'player': (47, 98, 16, 16),
    'enemy_rat': (32, 228, 16, 16),
    'enemy_goblin': (32, 276, 16, 16),
    'enemy_skel': (66, 321, 16, 16),
    'mimic': (112, 369, 16, 16),
    'chest': (129, 595, 16, 16),
    'chest_open': (144, 593, 16, 16),
    'stairs_down': (192, 416, 16, 16),
    'stairs_up': (208, 416, 16, 16),
    'loot_weapon': (48, 719, 16, 16),
    'loot_armor': (97, 738, 16, 16),
    'loot_potion': (82, 675, 16, 16),
    'key': (208, 594, 16, 16),
    'artifact': (80, 785, 16, 16),
    'grave': (49, 609, 16, 16)
}