import libtcodpy as libtcod
import math
import textwrap
import game_settings as opt
import shelve



color_noise = libtcod.noise_new(2)

color_dark_wall = libtcod.Color(31, 31, 39)
bgcolor_dark_wall = libtcod.Color(31, 31, 39)
color_light_wall = libtcod.Color(80,80,77)
bgcolor_light_wall = libtcod.Color(50,50,48)
color_dark_ground = libtcod.Color(3, 3, 5)
bgcolor_dark_ground = libtcod.Color(20, 20, 26)
color_light_ground = libtcod.Color(80,80,77)
bgcolor_light_ground = libtcod.Color(32,32,29)

# TODO
# Generalize map code.
# Starting with Tile, I added four new options. default_fg, default_bg, default_char, and tile_name
# I will probably set something up so instead of setting tiles to blocked to determine if they're a wall,
# I'll instead just set the tile's tile_name to 'wall'
# When rendering, Instead of checking if it's blocked, I will just check for 'wall' or 'floor'
class Tile:
    # def __init__(self, blocked, block_sight = None):
    #     self.blocked = blocked
    #     self.explored = False
    def __init__(self, blocked, block_sight = None,
                 # light_fg=libtcod.red,
                 # light_bg=libtcod.darkest_red,
                 # dark_fg=libtcod.red,
                 # dark_bg=libtcod.darkest_red,
                 # default_char='X',
                 light_fg=None,
                 light_bg=None,
                 dark_fg=None,
                 dark_bg=None,
                 default_char=None,
                 tile_name=None,
                 tile_x=None, tile_y=None):
        self.fg_light = light_fg
        self.fg_dark = dark_fg
        self.bg_light = light_bg
        self.bg_dark = dark_bg
        self.char = default_char
        self.blocked = blocked
        self.explored = False
        self.x = tile_x
        self.y = tile_y
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight


class Rect:
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1)


class Object:
    def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None, item=None):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.blocks = blocks
        self.fighter = fighter
        if self.fighter:
            self.fighter.owner = self
        self.ai = ai
        if self.ai:
            self.ai.owner = self
        self.item = item
        if self.item:
            self.item.owner = self

    def move(self, dx, dy):
        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy
        fov_recompute = True

    def draw(self):
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            libtcod.console_set_default_foreground(con, self.color)
            libtcod.console_put_char_ex(con, self.x, self.y, self.char, self.color,
                                        noisemap_color(bgcolor_light_ground, self.x, self.y))

    def clear(self):
        if map[self.x][self.y].explored:
            if libtcod.map_is_in_fov(fov_map, self.x, self.y):
                libtcod.console_put_char_ex(con, self.x, self.y, '.', color_light_ground,
                                            noisemap_color(bgcolor_light_ground, self.x, self.y))
            else:
                libtcod.console_put_char_ex(con, self.x, self.y, '.', color_dark_ground,
                                            noisemap_color(bgcolor_dark_ground, self.x, self.y))
        else:
            libtcod.console_put_char_ex(con, self.x, self.y, ' ', color_dark_ground, libtcod.black)

    def distance_to(self, other):
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def distance(self, x, y):
        return math.sqrt((x - self.x) ** 2 + ((y - self.y) ** 2))

    def move_towards(self, target_x, target_y):
        path = libtcod.path_new_using_map(fov_map)
        libtcod.path_compute(path, self.x, self.y, target_x, target_y)
        dx, dy = libtcod.path_get(path, 0)
        self.move_absolute(dx, dy)
        libtcod.path_delete(path)


        # dx = target_x - self.x
        # dy = target_y - self.y
        # if dx > 0:
        #     dx = 1
        # if dx < 0:
        #     dx = -1
        # if dy > 0:
        #     dy = 1
        # if dy < 0:
        #     dy = -1
        # self.moveai(dx, dy)

    def move_absolute(self, dx, dy):
        if not is_blocked(dx, dy):
            self.x = dx
            self.y = dy

    def moveai(self, dx, dy):
        if not is_blocked(self.x, self.y + dy):
            self.y += dy
        if not is_blocked(self.x + dx, self.y):
            self.x += dx

    def send_to_back(self):
        global objects
        objects.remove(self)
        objects.insert(0, self)


class Fighter:
    # Combat methods/properties
    def __init__(self, hp, defense, power, death_function=None):
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power
        self.death_function = death_function

    def attack(self, target):
        damage = self.power - target.fighter.defense

        if damage > 0:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' damage',
                    libtcod.dark_flame)
            target.fighter.take_damage(damage)
        else:
            print self.owner.name.capitalize() + ' attacks ' + target.name + ' but is too weak to be a threat!'

    def take_damage(self, damage):
        if damage > 0:
            self.hp -= damage
        if self.hp <= 0:
            function = self.death_function
            if function is not None:
                function(self.owner)

    def heal(self, amount):
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp


class BasicMonster:
    # AI for basic monster
    def take_turn(self):
        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 2:
                monster.move_towards(player.x, player.y)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)


class ConfusedMonster:
    def __init__(self, old_ai, num_turns_min, num_turns_max):
        self.old_ai = old_ai
        self.num_turns = libtcod.random_get_int(0, num_turns_min, num_turns_max)

    def take_turn(self):
        if self.num_turns > 0:
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
            self.num_turns += -1
        else:
            self.owner.ai = self.old_ai
            message('The ' + self.owner.name + ' has shaken off the confusion!', libtcod.light_azure)


class Item:
    def __init__(self, use_function=None):
        self.use_function = use_function

    def use(self):
        if self.use_function is None:
            message('You wave the ' + self.owner.name + ' around but nothing interesting happens', libtcod.yellow)
        else:
            if self.use_function() != 'cancelled':
                inventory.remove(self.owner)

    def pick_up(self):
        if len(inventory) >= 26:
            message('You have no room for the ' + self.owner.name + '.', libtcod.dark_red)
        else:
            inventory.append(self.owner)
            objects.remove(self.owner)
            message('Picked up the ' + self.owner.name + '.', libtcod.desaturated_green)

    def drop(self):
        objects.append(self.owner)
        inventory.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        message('Dropped a ' + self.owner.name, libtcod.yellow)


class Cursor:
    def __init__(self, x, y, bgcolor, fgcolor, drawn=False, radius=1):
        self.x = x
        self.y = y
        self.bgcolor = bgcolor
        self.fgcolor = fgcolor
        self.drawn = False
        self.radius = radius

    def toggle(self):
        self.drawn = not self.drawn

    def draw_bg(self):
        # Data for future volumetric spell areas
        # Number of tiles covered by given radius
        # radius=0 covers 1 tile
        # radius=1 covers 4
        # radius=2 covers 13
        # radius=3 covers 29
        # radius=4 covers 49
        # radius=5 covers 81
        if self.y >= 0 and self.x >= 0:
            # libtcod.console_set_char_background(con, self.x, self.y, self.bgcolor)
            for y in range(self.y - (self.radius + 1), self.y + (self.radius + 1)):
                for x in range(self.x - (self.radius + 1), self.x + (self.radius + 1)):
                    if self.dist_from(x, y) <= self.radius:
                        libtcod.console_set_char_background(con, x, y, self.bgcolor)



    def dist_from(self, other_x, other_y):
        dx = other_x - self.x
        dy = other_y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def spawn(self, spawner):
        if self.x == -1:
            self.x = spawner.x
        if self.y == -1:
            self.y = spawner.y

    def despawn(self):
        if self.x and self.y:
            self.x = -1
            self.y = -1

    def clear(self):
        x = self.x
        y = self.y
        for y in range(self.y - (self.radius + 1), self.y + (self.radius + 1)):
            for x in range(self.x - (self.radius + 1), self.x + (self.radius + 1)):
                if map[x][y].explored:
                    if libtcod.map_is_in_fov(fov_map, x, y):
                        libtcod.console_set_char_background(con, x, y, map[x][y].bg_light)
                    else:
                        libtcod.console_set_char_background(con, x, y, map[x][y].bg_dark)
                else:
                    libtcod.console_set_char_background(con, x, y, libtcod.black)


    def move_cursor(self, x, y):
        if self.x + x < 0:
            self.x = 0
        elif self.x + x > opt.MAP_WIDTH - 1:
            self.x = opt.MAP_WIDTH - 1
        else:
            self.x += x
        if self.y + y < 0:
            self.y = 0
        elif self.y + y > opt.MAP_HEIGHT - 1:
            self.y = opt.MAP_HEIGHT - 1
        else:
            self.y += y


def is_blocked(x, y):
    if map[x][y].blocked:
        return True

    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True

    return False


def create_room(room):
    global map
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            # map[x][y].blocked = False
            # map[x][y].block_sight = False
            process_tile(map[x][y], x, y, 'floor')
            # map[x][y].tile_x = float(x)
            # map[x][y].tile_y = float(y)
            # map[x][y].tile_name - 'floor'


def create_h_tunnel(x1, x2, y):
    global map
    for x in range(min(x1, x2), max(x1, x2) + 1):
        # map[x][y].blocked = False
        # map[x][y].block_sight = False
        # map[x][y].tile_name = 'floor'
        # map[x][y].tile_x = float(x)
        # map[x][y].tile_y = float(y)
        process_tile(map[x][y], x, y, 'floor')


def create_v_tunnel(y1, y2, x):
    global map
    for y in range(min(y1, y2), max(y1, y2) + 1):
        # map[x][y].blocked = False
        # map[x][y].block_sight = False
       # map[x][y].tile_name = 'floor'
        # map[x][y].tile_x = float(x)
        # map[x][y].tile_y = float(y)
       process_tile(map[x][y], x, y, 'floor')


def process_tile(tile, x_value, y_value, tilename):
    # This will probably be where I put my colors, chars, etc.
    # Probably something like if map_type = 'stone_dungeon' then wall are these colors, floor are these, etc.
    x = x_value
    y = y_value


    if tilename == 'floor':
        tile.tile_name = 'floor'
        tile.fg_light = noisemap_color(color_light_ground, x, y)
        tile.fg_dark = noisemap_color(color_dark_ground, x, y)
        tile.bg_light = noisemap_color(bgcolor_light_ground, x, y)
        tile.bg_dark = noisemap_color(bgcolor_dark_ground, x, y)
        tile.blocked = False
        tile.block_sight = False
        tile.char = '.'
    elif tilename == 'wall':
        tile.tile_name = 'wall'
        tile.fg_light = noisemap_color(color_light_wall, x, y)
        tile.fg_dark = noisemap_color(color_dark_wall, x, y)
        tile.bg_light = noisemap_color(bgcolor_light_wall, x, y)
        tile.bg_dark = noisemap_color(bgcolor_dark_wall, x, y)
        tile.char = '#'
        tile.blocked = True
        tile.block_sight = True


def make_map():
    global map, objects, cursors

    objects = [player]


    cursors = [target_cursor]


    map = [[ Tile(True, tile_name='wall')
        for y in range(opt.MAP_HEIGHT) ]
            for x in range(opt.MAP_WIDTH) ]

    for y in range(opt.MAP_HEIGHT):
        for x in range(opt.MAP_WIDTH):
            process_tile(map[x][y], x, y, 'wall')


    rooms = []
    num_rooms = 0

    for r in range(opt.MAX_ROOMS):
        # Random width/height within bounds of MIN and MAX size
        w = libtcod.random_get_int(0, opt.ROOM_MIN_SIZE, opt.ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, opt.ROOM_MIN_SIZE, opt.ROOM_MAX_SIZE)
        # Random position within bounds of map
        x = libtcod.random_get_int(0, 0, opt.MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, opt.MAP_HEIGHT - h - 1)

        new_room = Rect(x, y, w, h)

        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break
        if not failed:
            create_room(new_room)
            (new_x, new_y) = new_room.center()

            if num_rooms == 0:
                player.x = new_x
                player.y = new_y
            else:
                (prev_x, prev_y) = rooms[num_rooms - 1].center()

                if libtcod.random_get_int(0, 0, 1) == 1:
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)
            place_objects(new_room)
            rooms.append(new_room)
            num_rooms += 1


def place_objects(room):
    num_monsters = libtcod.random_get_int(0, 0, opt.MAX_ROOM_MONSTERS)
    num_items = libtcod.random_get_int(0, 0, opt.MAX_ROOM_ITEMS)

    for i in range(num_monsters):
        x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcod.random_get_int(0, room.y1+ 1, room.y2 - 1)

        if not is_blocked(x, y):
            # if libtcod.random_get_int(0, 0, 100) < 80:
            #     fighter_component = Fighter(hp=10, defense=0, power=3, death_function=monster_death)
            #     ai_component = BasicMonster()
            #     monster = Object(x, y, 'd', 'doge', libtcod.light_amber,
            #                      blocks=True, fighter=fighter_component, ai=ai_component)
            # else:
            #     fighter_component=Fighter(hp=16, defense=1, power=4, death_function=monster_death)
            #     ai_component=BasicMonster()
            #     monster = Object(x, y, 'D', 'big doge', libtcod.amber, blocks=True,
            #                      fighter=fighter_component, ai=ai_component)

            # Sets chosen - to a random mob name from the monster list
            choice = random_choice(monster_list)
            mob_stats = []
            # Sets mob_stats equal to a list of the monster's stats
            # In format [char, color, hp, def, power, death_function, ai_component, blocks
            mob_name = choice.name
            mob_char = choice.char
            mob_color = choice.color
            mob_hp = choice.hp
            mob_def = choice.defense
            mob_power = choice.power
            mob_death = choice.death_function
            mob_block = choice.blocks
            if choice.ai == 'basic':
                ai_component = BasicMonster()
            fighter_component = Fighter(hp=mob_hp, defense=mob_def, power=mob_power, death_function=mob_death)
            monster = Object(x, y, mob_char, mob_name, mob_color, blocks=mob_block,
                             fighter=fighter_component, ai=ai_component)

            objects.append(monster)

    for i in range(num_items):
        x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

        if not is_blocked(x, y):
            choice = random_choice(item_list)
            item_char = choice.char
            item_name = choice.name
            item_color = choice.color
            item_function = choice.function
            item_component = Item(use_function=item_function)
            item = Object(x, y, item_char, item_name, item_color, item=item_component)

            objects.append(item)
            item.send_to_back()


def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    bar_width = int(float(value) / maximum * total_width)

    # Render Background
    libtcod.console_set_default_background(panel, back_color)
    libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

    # Render bar on top
    libtcod.console_set_default_background(panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

    # Add text on top with the value
    libtcod.console_set_default_foreground(panel, libtcod.white)
    libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
                             name + ': ' + str(value) + '/' + str(maximum))


def get_names_under_mouse():
    global mouse

    (x, y) = (mouse.cx, mouse.cy)
    names = [obj.name for obj in objects
            if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]
    names = ', '.join(names)
    return names.capitalize()


def render_all():
    global color_light_wall, color_light_ground, color_dark_wall, color_dark_ground
    global fov_recompute

    if fov_recompute:
        fov_recompute = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, opt.TORCH_RADIUS, opt.FOV_LIGHT_WALLS, opt.FOV_ALGO)

        # Go through all tiles, and set their background color
        for y in range(opt.MAP_HEIGHT):
            for x in range(opt.MAP_WIDTH):
                visible = libtcod.map_is_in_fov(fov_map, x, y)
                if not visible:
                    if map[x][y].explored:
                        libtcod.console_put_char_ex(con, x, y, map[x][y].char, map[x][y].fg_dark, map[x][y].bg_dark)
                else:
                    libtcod.console_put_char_ex(con, x, y, map[x][y].char, map[x][y].fg_light, map[x][y].bg_light)
                    map[x][y].explored = True
                # wall = map[x][y].block_sight
                # if not visible:
                #     if map[x][y].explored:
                #         if wall:
                #             # libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
                #             #libtcod.console_put_char_ex(con, x, y, '#', noisemap_color(bgcolor_dark_wall, x, y),
                #             #                            noisemap_color(bgcolor_dark_wall, x, y))
                #
                #         else:
                #             # libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
                #             libtcod.console_put_char_ex(con, x, y, '.', noisemap_color(color_dark_ground, x, y),
                #                                         noisemap_color(bgcolor_dark_ground, x, y))
                #
                # else:
                #     if wall:
                #         # libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET)
                #         libtcod.console_put_char_ex(con, x, y, '#', noisemap_color(color_light_wall, x, y),
                #                                     noisemap_color(bgcolor_light_wall, x, y))
                #     else:
                #         # libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET)
                #         libtcod.console_put_char_ex(con, x, y, '.', noisemap_color(color_light_ground, x, y),
                #                                     noisemap_color(bgcolor_light_ground, x, y))
                #     map[x][y].explored = True

    # draw all objects in the list
    for object in objects:
        if object != player:
            object.draw()
        player.draw()

    # Draw cursors after objects, so the bg color shows up behind them when they're targeted
    for cursor in cursors:
        if cursor.drawn:
            cursor.draw_bg()

    # blit the contents of "con" to the root console
    libtcod.console_blit(con, 0, 0, opt.MAP_WIDTH, opt.MAP_HEIGHT, 0, 0, 0)

    # Setup for rendering GUI panel
    libtcod.console_set_default_background(panel, libtcod.black)
    libtcod.console_clear(panel)

    # Print game messages one by one
    y = 1
    for (line, color) in game_msgs:
        libtcod.console_set_default_foreground(panel, color)
        libtcod.console_print_ex(panel, opt.MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
        y += 1

    # Display names of things under mouse
    libtcod.console_set_default_foreground(panel, libtcod.light_gray)
    libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())


    # Render health bar
    render_bar(1, 1, opt.BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp,
               libtcod.darker_green, libtcod.darkest_red)
    libtcod.console_blit(panel, 0, 0, opt.SCREEN_WIDTH, opt.PANEL_HEIGHT, 0, 0, opt.PANEL_Y)


def message(new_msg, color = libtcod.white):
    new_msg_lines = textwrap.wrap(new_msg, opt.MSG_WIDTH)

    for line in new_msg_lines:
        if len(game_msgs) == opt.MSG_HEIGHT:
            del game_msgs[0]
        game_msgs.append( (line, color) )


def player_move_or_attack(dx, dy):
    global fov_recompute
    x = player.x + dx
    y = player.y + dy

    target = None
    for object in objects:
        if object.x == x and object.y == y and object.fighter:
            target = object
            break

    if target is not None:
        player.fighter.attack(target)
        fov_recompute = True
    else:
        player.move(dx, dy)
        fov_recompute = True


def closest_monster(max_range):
    closest_enemy = None
    closest_dist = max_range + 1

    for object in objects:
        if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
            dist = player.distance_to(object)
            if dist < closest_dist:
                closest_enemy = object
                closest_dist = dist
    return closest_enemy


def reset_map_color(x, y):
    if map[x][y].explored:
        if libtcod.map_is_in_fov(fov_map, x, y):
            libtcod.console_put_char_ex(con, x, y, '.', color_light_ground,
                                        noisemap_color(bgcolor_light_ground, x, y))
        else:
            libtcod.console_put_char_ex(con, x, y, '.', color_dark_ground,
                                        noisemap_color(bgcolor_dark_ground, x, y))
    else:
        libtcod.console_put_char_ex(con, x, y, ' ', color_dark_ground, libtcod.black)


def menu(header, options, width):
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options')
    # Calc the header height after auto-wrap, one line per option
    header_height = libtcod.console_get_height_rect(con, 0, 0, width, opt.SCREEN_HEIGHT, header)
    if header == '':
        header_height = 0
    height = len(options) + header_height
    # Create new offscreen window
    window = libtcod.console_new(width, height)
    # Print header with auto-wrap
    libtcod.console_set_default_foreground(window, libtcod.Color(230,230,230))
    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)
    # Print options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        # Print options in format a) Option
        text = chr(letter_index) + ')  ' + option_text
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
        y += 1
        letter_index += 1
    x = opt.SCREEN_WIDTH/2 - width/2
    y = opt.SCREEN_HEIGHT/2 - height/2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)
    if key.vk == libtcod.KEY_ENTER and key.lalt:
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    # If an item was chosen, return it
    index = key.c - ord('a')
    if index >= 0 and index < len(options): return index
    return None


def msgbox(text, width=50):
    menu(text, [], width)


def inventory_menu(header):
    if len(inventory) == 0:
        options = ['Inventory is empty']
    else:
        options = [item.name for item in inventory]

    index = menu(header, options, opt.INVENTORY_WIDTH)

    if index is None or len(inventory) == 0: return None
    return inventory[index].item


def handle_keys():
    global fov_recompute, game_state
    global key

    if key.vk == libtcod.KEY_ENTER and key.lalt:
        # Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit'  # exit game

    if game_state == 'playing':
        # movement keys
        if key.vk == libtcod.KEY_UP:
            player_move_or_attack(0, -1)
        elif key.vk == libtcod.KEY_KP8:
            player_move_or_attack(0, -1)

        elif key.vk == libtcod.KEY_DOWN:
            player_move_or_attack(0, 1)
        elif key.vk == libtcod.KEY_KP2:
            player_move_or_attack(0, 1)

        elif key.vk == libtcod.KEY_LEFT:
            player_move_or_attack(-1, 0)
        elif key.vk == libtcod.KEY_KP4:
            player_move_or_attack(-1, 0)

        elif key.vk == libtcod.KEY_RIGHT:
            player_move_or_attack(1, 0)
        elif key.vk == libtcod.KEY_KP6:
            player_move_or_attack(1, 0)

        elif key.vk == libtcod.KEY_KP1:
            player_move_or_attack(-1, 1)

        elif key.vk == libtcod.KEY_KP3:
            player_move_or_attack(1, 1)

        elif key.vk == libtcod.KEY_KP7:
            player_move_or_attack(-1, -1)

        elif key.vk == libtcod.KEY_KP9:
            player_move_or_attack(1, -1)

        elif key.vk == libtcod.KEY_KP5:
            player.move(0, 0)
            fov_recompute = True

        else:
            key_char = chr(key.c)
            item_picked_up = None
            if key_char == ',' or key_char == 'g':
                for object in objects:
                    if object.x == player.x and object.y == player.y and object.item:
                        object.item.pick_up()
                        item_picked_up = True
                        break
                if not item_picked_up:
                    message('Nothing to pick up', libtcod.light_crimson)
            if key_char == 'i':
                chosen_item = inventory_menu('Press the key next to an item to use it, or any other key to cancel.\n')
                if chosen_item is not None:
                    chosen_item.use()
            if key_char == 'd':
                chosen_item = inventory_menu('Choose an item to drop\n')
                if chosen_item is not None:
                    chosen_item.drop()

            return 'didnt-take-turn'


def monster_target_check(query_x, query_y):
    # Loop through all objects
    for possible_target in objects:
        # Check if the player can see them, and if they're actually a Fighter
        if libtcod.map_is_in_fov(fov_map, query_x, query_y) and possible_target.fighter:
            # And if so, check if they match the position of the queried location
            if possible_target.x == query_x and possible_target.y == query_y:
                return possible_target
    # If the function makes it this far, nothing matches so no target is returned
    return None


def keyboard_target(radius=1, color=libtcod.light_orange, needs_obj=True):

    libtcod.console_flush()
    tar_x = None
    tar_y = None
    target_acquired = None
    message('Choose a target using the keypad. Make your selection with the enter key.', libtcod.light_azure)


    # Run this loop while no target has been found
    while not target_acquired:

        # Initialize the cursor. Set its color and radius
        target_cursor.bgcolor = color
        target_cursor.radius = radius

        # If the cursor is not currently being drawn, toggle it on
        if not target_cursor.drawn:
            target_cursor.toggle()

        # Set the cursor's x and y coords
        if target_cursor.x == -1 and target_cursor.y == -1:
            target_cursor.spawn(player)

        # Set the color of the cursor. For now, it's only orange.
        # Maybe pass the color along when calling keyboard_target()?
        # Like target = keyboard_target(libtcod.light_orange)
        target_cursor.bgcolor = color

        # The cursor is drawn in this step, after all objects, to allow it to set the background.
        render_all()

        # HOPEFULLY works properly and clears the cursor before the next frame is drawn.
        if target_cursor.y and target_cursor.x:
            target_cursor.clear()
        #libtcod.console_set_char_background(con, tar_x, tar_y, libtcod.light_orange)
        libtcod.console_flush()

        # Begin checking for keypresses. These keypresses will not advance a game turn.
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE, key, mouse)
        if not tar_x:
            tar_x = player.x
        if not tar_y:
            tar_y = player.y
        if key.vk == libtcod.KEY_KP8:
            tar_y += -1
            target_cursor.move_cursor(0, -1)
        elif key.vk == libtcod.KEY_KP2:
            tar_y += 1
            target_cursor.move_cursor(0, 1)
        elif key.vk == libtcod.KEY_KP4:
            tar_x += -1
            target_cursor.move_cursor(-1, 0)
        elif key.vk == libtcod.KEY_KP6:
            tar_x += 1
            target_cursor.move_cursor(1, 0)
        elif key.vk == libtcod.KEY_KP1:
            tar_y += 1
            tar_x += -1
            target_cursor.move_cursor(-1, 1)
        elif key.vk == libtcod.KEY_KP3:
            tar_y += 1
            tar_x += 1
            target_cursor.move_cursor(1, 1)
        elif key.vk == libtcod.KEY_KP7:
            tar_y += -1
            tar_x += -1
            target_cursor.move_cursor(-1, -1)
        elif key.vk == libtcod.KEY_KP9:
            tar_y += -1
            tar_x += 1
            target_cursor.move_cursor(1, -1)
        elif key.vk == libtcod.KEY_KPENTER:
            target_acquired = monster_target_check(tar_x, tar_y)
            if needs_obj:
                if target_acquired == None:
                    message('No target! Try again or press a non-targeting key to cancel.', libtcod.yellow)
                else:
                    if target_cursor.drawn:
                        target_cursor.toggle()
                    if target_cursor.x >= 0 or target_cursor.y >= 0:
                        target_cursor.x = -1
                        target_cursor.y = -1
                    return target_acquired
            elif not needs_obj:
                if target_cursor.drawn:
                    target_cursor.toggle()
                if target_cursor.x >= 0 or target_cursor.y >= 0:
                    target_cursor.x = -1
                    target_cursor.y = -1
                return tar_x, tar_y
        elif key.vk:
            if target_cursor.drawn:
                target_cursor.toggle()
            if target_cursor.x or target_cursor.y:
                target_cursor.x = -1
                target_cursor.y = -1
            if needs_obj:
                return 'cancelled', 'cancelled'
            return 'cancelled'


def player_death(player):
    global game_state
    message('You died!', libtcod.red)
    game_state = 'dead'
    player.char = '%'
    player.color = libtcod.darker_gray


def monster_death(monster):
    message(monster.name.capitalize() + ' has fallen', libtcod.azure)
    monster.char = '%'
    monster.color = libtcod.darker_gray
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = monster.name + ' corpse'
    monster.send_to_back()


def player_light_healing_potion():
    # heal the player for 5-15% health
    if player.fighter.hp == player.fighter.max_hp:
        message('You are already at full health.', libtcod.red)
        return 'cancelled'
    min_amount = int(math.ceil(player.fighter.max_hp *.05))
    max_amount = int(math.ceil(player.fighter.max_hp * .1))

    amount = libtcod.random_get_int(0, min_amount, max_amount)
    message('Healing for ' + str(min_amount) + ' - ' + str(max_amount))
    message('Your wounds start to feel better! You are healed for ' + str(amount) + ' hp.', libtcod.light_violet)
    player.fighter.heal(amount)


def player_static_shock():
    target = closest_monster(10)
    damage = libtcod.random_get_int(0, 2, 10)
    if target is None:
        message('Static discharges into the air around you and dissipates', libtcod.yellow)
        return
    message('A static bolt discharges and strikes ' + target.name + '!', libtcod.light_azure)
    target.fighter.take_damage(damage)


def player_force_bolt():
    target = keyboard_target(radius=0)
    damage = libtcod.random_get_int(0,6,8)
    if target == 'cancelled':
        message('A gentle wave of force passes around you.', libtcod.yellow)
        return
    message('A globe of force flies towards the ' + target.name + ' and strikes it!', libtcod.light_azure)
    target.fighter.take_damage(damage)


def player_fireball():
    tar_x, tar_y = keyboard_target(radius=2, needs_obj=False)
    if tar_x == 'cancelled':
        message('Your body feels warmer for a moment, and you feel a sense of wasted power', libtcod.yellow)
        return
    for obj in objects:
        if obj.distance(tar_x, tar_y) <= 2 and obj.fighter:
            obj.fighter.take_damage(libtcod.random_get_int(0,6, 10))
    message('The fireball flies away from you and explodes in a cloud of conflagration, burning all caught inside',
            libtcod.light_azure)


def player_cast_confusion():
    monster = closest_monster(12)
    if monster is None:
        message('The air around you ebbs slightly.', libtcod.yellow)
        return
    old_ai = monster.ai
    monster.ai = ConfusedMonster(old_ai, 6, 12)
    monster.ai.owner = monster
    message('The ' + monster.name + ' looks dazed and stumbles around aimlessly', libtcod.light_azure)


def noisemap_color(based_on, x, y):
    # # Smoother, more like gradients you'd see in Brogue
    # f = [x*.2, y*.2]
    # noise_value = libtcod.noise_get(color_noise, f, 32)
    # color_multiplier = noise_value*.22+.9

    # # Blotchier, looks better with subtler colors
    x = x * 1.0
    y = y * 1.0
    f = [x, y]
    noise_value = libtcod.noise_get(color_noise, f, 8)
    color_multiplier = noise_value * .1 + .92
    final_color = based_on * color_multiplier
    return final_color


def setup_chance_dictionary(dict):
    # Create blank dictionary
    # This will end up in the format name:chance (such as goblin: 40 or healing_potion: 75)
    chance_dict = {}
    for key in dict.keys():
        chance_dict[key] = dict[key][1]

    return chance_dict


def choose_random_entry(c_dict):
    chances = c_dict.values()
    key_names = c_dict.keys()


    # Choose random int from 1 to the sum of all chances in the dict
    chance_value = libtcod.random_get_int(0, 1, sum(chances))
    running_total = 0
    c_index = 0

    # Determines the chosen key.
    # Starts at 0, adds each chance in order from the chance_dict passed to this function.
    # When the total is greater than the random number chosen, break the loop and pass the
    # key paired to the value that was added.
    for i in chances:
        running_total += i
        if running_total >= chance_value:
            return key_names[c_index]
        c_index += 1


def random_choice(choice_dict):
    # Function to choose a random entry from given dictionary choice_dict.
    # choice_dict should be in the format choice_dict[key] = [object_to_pass, int(chance)]
    # Function returns the actual object that is chosen

    # First define chance_dictionary as a dict
    chance_dictionary = {}

    # Then fill it with entries of name : chance
    chance_dictionary = setup_chance_dictionary(choice_dict)

    # Pass it to a function that picks a random entry from it and returns the key
    choice_key = choose_random_entry(chance_dictionary)

    # Finally, return the monster object associated with the chosen key
    return choice_dict[choice_key][0]


def tile_dist_from_player(tile_x, tile_y):
    dx = tile_x - player.x
    dy = tile_y - player.y
    return math.sqrt(dx ** 2 + dy ** 2)

#####################################
#    Item and Monster Components    #
#      MUST go above this box.      #
#####################################
#    Below are monster and item     #
#      definitions and chances      #
#####################################

# Monster Class
class MonsterData:
    def __init__(self, name, char, color, hp, defense, power, death_function=monster_death, ai_component='basic',
                 blocks=True):
        self.name = name
        self.char = char
        self.color = color
        self.hp = hp
        self.defense = defense
        self.power = power
        self.death_function = death_function
        self.ai = ai_component
        self.blocks = blocks


# Item Class
class ItemData:
    def __init__(self, char, name, color, function):
        self.char = char
        self.name = name
        self.color = color
        self.function = function

#     DEFINE MONSTERS     #

doge = MonsterData('doge', 'd', libtcod.light_amber, 10, 0, 3)
big_doge = MonsterData('big doge', 'D', libtcod.amber, 16, 1, 4)
blue_doge = MonsterData('blue doge', 'd', libtcod.blue, 10, 0, 3)


#      DEFINE ITEMS       #

potion_light_heal = ItemData('!', 'light healing potion', libtcod.crimson, player_light_healing_potion)
scroll_static_shock = ItemData('?', 'scroll of static shock', libtcod.white, player_static_shock)
scroll_force_bolt = ItemData('?', 'scroll of force bolt', libtcod.white, player_force_bolt)
scroll_confusion = ItemData('?', 'scroll of confusion', libtcod.white, player_cast_confusion)
scroll_fireball = ItemData('?', 'scroll of fireball', libtcod.white, player_fireball)


#     Monster Chances     #
monster_list = {}
monster_list["doge"] = [doge, 80]
monster_list["big doge"] = [big_doge, 20]
monster_list["blue doge"] = [blue_doge, 100]

#       Item Chances      #
item_list = {}
item_list["light healing potion"] = [potion_light_heal, 50]
item_list["scroll of static shock"] = [scroll_static_shock, 20]
item_list["scroll of force bolt"] = [scroll_force_bolt, 20]
item_list["scroll of confusion"] = [scroll_confusion, 20]
item_list["scroll of fireball"] = [scroll_fireball, 100]

# MAIN #




def new_game():
    global player, inventory, game_msgs, game_state, target_cursor

    # Create player object
    fighter_component=Fighter(hp=30,
                              defense=2,
                              power=5,
                              death_function=player_death)
    player = Object(0, 0, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component)

    target_cursor = Cursor(-1, -1, libtcod.black, libtcod.black)

    make_map()
    initialize_fov()

    game_state = 'playing'
    inventory = []
    game_msgs = []

    message('Welcome to the unnamed dungeon', libtcod.crimson)


def initialize_fov():
    global fov_recompute, fov_map
    libtcod.console_clear(con)
    fov_recompute = True
    fov_map = libtcod.map_new(opt.MAP_WIDTH, opt.MAP_HEIGHT)
    for y in range(opt.MAP_HEIGHT):
        for x in range(opt.MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)


def play_game():
    global key, mouse

    player_action = None

    mouse = libtcod.Mouse()
    key = libtcod.Key()

    while not libtcod.console_is_window_closed():

        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE, key, mouse)

        # render the screen
        render_all()

        libtcod.console_flush()

        # erase all objects at their old locations, before they move
        for object in objects:
            object.clear()

        # handle keys and exit game if needed
        # noinspection PyRedeclaration
        player_action = handle_keys()
        if player_action == 'exit':
            save_game()
            break

        # Give monsters their turn
        if game_state == 'playing' and player_action != 'didnt-take-turn':
            for object in objects:
                if object.ai:
                    object.ai.take_turn()


def save_game():
    file=shelve.open('savegame', 'n')
    file['map'] = map
    file['objects'] = objects
    file['inventory'] = inventory
    file['game_msgs'] = game_msgs
    file['game_state'] = game_state
    file['player_index'] = objects.index(player)
    file['cursors'] = cursors
    file.close()


def load_game():
    global map, objects, player, inventory, game_msgs, game_state, cursors
    file=shelve.open('savegame', 'r')
    map = file['map']
    objects = file['objects']
    player = objects[file['player_index']]
    inventory = file['inventory']
    game_msgs = file['game_msgs']
    game_state = file['game_state']
    cursors = file['cursors']
    file.close()

    initialize_fov()


def main_menu():
    libtcod.console_set_default_foreground(0, libtcod.amber)
    libtcod.console_print_ex(0, opt.SCREEN_WIDTH/2, opt.SCREEN_HEIGHT/2-8, libtcod.BKGND_NONE, libtcod.CENTER,
                         'DOGELIKE')
    libtcod.console_print_ex(0, opt.SCREEN_WIDTH/2, opt.SCREEN_HEIGHT/2-6, libtcod.BKGND_NONE, libtcod.CENTER,
                         'Such hack, very procedural, so loot wow')
    while not libtcod.console_is_window_closed():
        choice = menu('', ['new game, so scare', 'wow continue', 'plz no quit'], 26)

        if choice == 0:
            new_game()
            play_game()
        elif choice == 1:
            try:
                load_game()
            except:
                msgbox('\nNo saved game!\n', 24)
                continue
            play_game()
        elif choice == 2:
            break

#############################################
# Initialization & Main Loop
#############################################
 
#libtcod.console_set_custom_font('lucida12x12_gs_tc.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_set_custom_font('meiryu_11.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_ASCII_INROW)
libtcod.console_init_root(opt.SCREEN_WIDTH, opt.SCREEN_HEIGHT, 'python/libtcod tutorial', False)
libtcod.sys_set_fps(opt.LIMIT_FPS)
con = libtcod.console_new(opt.SCREEN_WIDTH, opt.SCREEN_HEIGHT)
panel = libtcod.console_new(opt.SCREEN_WIDTH, opt.PANEL_HEIGHT)

# libtcod.console_set_default_foreground(0, libtcod.amber)
# libtcod.console_print_ex(0, opt.SCREEN_WIDTH/2, opt.SCREEN_HEIGHT/2-8, libtcod.BKGND_NONE, libtcod.CENTER,
#                          'DOGELIKE')
# libtcod.console_print_ex(0, opt.SCREEN_WIDTH/2, opt.SCREEN_HEIGHT/2-6, libtcod.BKGND_NONE, libtcod.CENTER,
#                          'Such hack, very procedural, so loot wow')

main_menu()
 
# create object representing the player
# fighter_component = Fighter(hp=34, defense=2, power=5, death_function=player_death)
# player = Object(0, 0, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component)

# the list of objects to start
# objects = [player]
#
#
# target_cursor = Cursor(-1, -1, libtcod.black, libtcod.black)
# cursors = [target_cursor]


 
# generate map (at this point it's not drawn to the screen)
# make_map()

# fov_map = libtcod.map_new(opt.MAP_WIDTH, opt.MAP_HEIGHT)
# for y in range(opt.MAP_HEIGHT):
#     for x in range(opt.MAP_WIDTH):
#         libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)
# path = libtcod.path_new_using_map(fov_map)

# fov_recompute = True
# game_state = 'playing'
# player_action = None

# game_msgs = []

# message('Welcome to Dogelike! So procedurally, such orcs and trolls, wow wow', libtcod.lighter_cyan)

# mouse = libtcod.Mouse()
# key = libtcod.Key()

# inventory = []

# while not libtcod.console_is_window_closed():
#
#     libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE, key, mouse)
#
#     # render the screen
#     render_all()
#
#     libtcod.console_flush()
#
#     # erase all objects at their old locations, before they move
#     for object in objects:
#         object.clear()
#
#     # handle keys and exit game if needed
#     # noinspection PyRedeclaration
#     player_action = handle_keys()
#     if player_action == 'exit':
#         break
#
#     # Give monsters their turn
#     if game_state == 'playing' and player_action != 'didnt-take-turn':
#         for object in objects:
#             if object.ai:
#                 object.ai.take_turn()

