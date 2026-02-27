import pygame
import time
import math
import os
import asyncio
from utils import scale_image, blit_rotate_center, blit_text_center

# --- 1. ÄÄNEN ALUSTUS ---
pygame.mixer.pre_init(44100, -16, 2, 1024)
pygame.mixer.init()

pygame.font.init()

# Ladataan kolariefekti kerran muistiin
CRASH_SOUND = None
try:
    # Varmista, että tiedosto löytyy sounds-kansiosta
    CRASH_SOUND = pygame.mixer.Sound(os.path.join("sounds", "crash.ogg"))
    CRASH_SOUND.set_volume(0.4)
except:
    print("Kolaritiedostoa ei löytynyt, peli jatkuu äänettömänä.")

# Kuvat ja asetukset (lähde: auto.zip)
GRASS = scale_image(pygame.image.load("imgs/ruoho1800.jpg"), 0.5)
TRACK = scale_image(pygame.image.load("imgs/track1.png"), 0.9)
TRACK_BORDER = scale_image(pygame.image.load("imgs/track-border3.png"), 0.9)
TRACK_BORDER_MASK = pygame.mask.from_surface(TRACK_BORDER)
FINISH = pygame.image.load("imgs/finish.png")
FINISH_MASK = pygame.mask.from_surface(FINISH)
FINISH_POSITION = (130, 250)
RED_CAR = scale_image(pygame.image.load("imgs/auto_pun.png"), 0.12)
GREEN_CAR = scale_image(pygame.image.load("imgs/auto_vih.png"), 0.06)

WIDTH, HEIGHT = TRACK.get_width(), TRACK.get_height()
WIN = pygame.display.set_mode((WIDTH, HEIGHT))

MAIN_FONT = pygame.font.SysFont("comicsans", 44)
FPS = 60
PATH = [(175, 119), (110, 70), (56, 133), (70, 481), (318, 731), (404, 680), (418, 521), (507, 475), (600, 551), (613, 715), (736, 713),
        (734, 399), (611, 357), (409, 343), (433, 257), (697, 258), (738, 123), (581, 71), (303, 78), (275, 377), (176, 388), (178, 260)]

# --- LUOKAT  ---
class GameInfo:
    LEVELS = 10
    def __init__(self, level=1):
        self.level = level
        self.started = False
        self.level_start_time = 0
        self.total_time = 0  # Uusi muuttuja kokonaisajalle

    def next_level(self):
        # Tallennetaan tähänastinen aika ennen tason vaihtoa
        self.total_time += self.get_level_time()
        self.level += 1
        self.started = False
    def reset(self):
        self.level = 1
        self.started = False
        self.level_start_time = 0
        self.total_time = 0  # Nollataan kokonaisaika resetoidessa

    def game_finished(self):
        return self.level > self.LEVELS
    
    def start_level(self):
        self.started = True
        self.level_start_time = time.time()

    def get_level_time(self):
        if not self.started: return 0
        return round(time.time() - self.level_start_time)

class AbstractCar:
    def __init__(self, max_vel, rotation_vel):
        self.img = self.IMG
        self.max_vel = max_vel
        self.vel = 0
        self.rotation_vel = rotation_vel
        self.angle = 0
        self.x, self.y = self.START_POS
        self.acceleration = 0.1
    def rotate(self, left=False, right=False):
        if left: self.angle += self.rotation_vel
        elif right: self.angle -= self.rotation_vel
    def draw(self, win):
        blit_rotate_center(win, self.img, (self.x, self.y), self.angle)
    def move_forward(self):
        self.vel = min(self.vel + self.acceleration, self.max_vel)
        self.move()
    def move_backward(self):
        self.vel = max(self.vel - self.acceleration, -self.max_vel/2)
        self.move()
    def move(self):
        radians = math.radians(self.angle)
        vertical = math.cos(radians) * self.vel
        horizontal = math.sin(radians) * self.vel
        self.y -= vertical
        self.x -= horizontal
    def collide(self, mask, x=0, y=0):
        car_mask = pygame.mask.from_surface(self.img)
        offset = (int(self.x - x), int(self.y - y))
        return mask.overlap(car_mask, offset)
    def reset(self):
        self.x, self.y = self.START_POS
        self.angle = 0
        self.vel = 0

class PlayerCar(AbstractCar):
    IMG = RED_CAR
    START_POS = (145, 200)

    def __init__(self, max_vel, rotation_vel):
        super().__init__(max_vel, rotation_vel)
        self.last_crash_time = 0  # Lisätään aikaleima

    def reduce_speed(self):
        self.vel = max(self.vel - self.acceleration / 2, 0)
        self.move()

    def bounce(self):
        self.vel = -self.vel / 1.5
        self.move()

        # Tarkistetaan, onko kulunut vähintään 0.3 sekuntia edellisestä äänestä
        current_time = time.time()
        if CRASH_SOUND and (current_time - self.last_crash_time > 0.3):
            CRASH_SOUND.play()
            self.last_crash_time = current_time

class ComputerCar(AbstractCar):
    IMG = GREEN_CAR
    START_POS = (175, 200)
    def __init__(self, max_vel, rotation_vel, path=[]):
        super().__init__(max_vel, rotation_vel)
        self.path = path
        self.current_point = 0
        self.vel = max_vel
    def calculate_angle(self):
        target_x, target_y = self.path[self.current_point]
        x_diff = target_x - self.x
        y_diff = target_y - self.y
        if y_diff == 0: desired_radian_angle = math.pi / 2
        else: desired_radian_angle = math.atan(x_diff / y_diff)
        if target_y > self.y: desired_radian_angle += math.pi
        diff = self.angle - math.degrees(desired_radian_angle)
        if diff >= 180: diff -= 360
        if diff > 0: self.angle -= min(self.rotation_vel, abs(diff))
        else: self.angle += min(self.rotation_vel, abs(diff))
    def update_path_point(self):
        target = self.path[self.current_point]
        rect = pygame.Rect(self.x, self.y, self.img.get_width(), self.img.get_height())
        if rect.collidepoint(*target): self.current_point += 1
    def move(self):
        if self.current_point >= len(self.path): return
        self.calculate_angle()
        self.update_path_point()
        super().move()

    def next_level(self, level):
        self.reset() # Tämä asettaa self.angle = 0
        self.vel = self.max_vel + (level - 1) * 0.2
        self.current_point = 0

# --- APUFUNKTIOT ---
async def handle_collision(player_car, computer_car, game_info):
    if player_car.collide(TRACK_BORDER_MASK) is not None:
        player_car.bounce()
        player_car.move()
    
    # KUN TIETOKONE VOITTAA:
    if computer_car.collide(FINISH_MASK, *FINISH_POSITION) is not None:
        # Piirretään teksti ruudulle ennen nollausta
        blit_text_center(WIN, MAIN_FONT, "COMPUTER WINS! TRY AGAIN.")
        pygame.display.update()
        
        # Odotetaan 2 sekuntia, jotta pelaaja ehtii lukea tekstin
        await asyncio.sleep(2)
        
        # Nollataan peli ja autot oikein
        game_info.reset()
        player_car.reset()
        computer_car.next_level(game_info.level) 

    player_finish_poi = player_car.collide(FINISH_MASK, *FINISH_POSITION) 
    if player_finish_poi is not None:
        if player_finish_poi[1] == 0: 
            player_car.bounce()
        else:
            game_info.next_level()
            player_car.reset()
            computer_car.next_level(game_info.level)

# Pääsilmukka (pidetään asynkronisena, jotta voimme käyttää awaitia törmäyksenhallinnassa)
async def main():
    run = True
    clock = pygame.time.Clock()
    images = [(GRASS, (0, 0)), (TRACK, (0, 0)), (FINISH, FINISH_POSITION), (TRACK_BORDER, (0, 0))]
    p_car = PlayerCar(4, 4)
    c_car = ComputerCar(2, 4, PATH)
    g_info = GameInfo()

    while run:
        clock.tick(FPS)
        
        # Piirtäminen
        for img, pos in images: WIN.blit(img, pos)
        level_text = MAIN_FONT.render(f"Level {g_info.level}", 1, (255, 255, 255))
        WIN.blit(level_text, (10, HEIGHT - 70))

        # LISÄYS: Kuluvan tason aika sekunteina
        # get_level_time() palauttaa ajan pyöristettynä sekunteina
        current_time = g_info.get_level_time()
        time_display = MAIN_FONT.render(f"Time: {current_time}s", 1, (255, 255, 255))
        WIN.blit(time_display, (10, HEIGHT - 120)) # Piirretään tasonumeron yläpuolelle

        p_car.draw(WIN)
        c_car.draw(WIN)
        pygame.display.update()

        while not g_info.started:
            blit_text_center(WIN, MAIN_FONT, f"Press any key to start level {g_info.level}!")
            pygame.display.update()
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN: g_info.start_level()
                if event.type == pygame.QUIT: return
            await asyncio.sleep(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: run = False

        # Liikkuminen
        keys = pygame.key.get_pressed()
        moved = False
        if keys[pygame.K_a]: p_car.rotate(left=True)
        if keys[pygame.K_d]: p_car.rotate(right=True)
        if keys[pygame.K_w]:
            moved = True
            p_car.move_forward()
        if keys[pygame.K_s]:
            moved = True
            p_car.move_backward()
        if not moved: p_car.reduce_speed()

        c_car.move()
        # Kutsu törmäyksenhallintaa await-sanalla, jotta se voi odottaa tarvittaessa
        await handle_collision(p_car, c_car, g_info)

        # --- LOPPURUUTU ---
        if g_info.game_finished():
            # Lasketaan viimeisen tason aika mukaan loppusummaan
            final_time = g_info.total_time + g_info.get_level_time()

            minutes = final_time // 60
            seconds = final_time % 60
            
            # Tyhjennetään ruutu ja näytetään lopputiedot
            WIN.fill((0, 0, 0)) # Musta tausta
            blit_text_center(WIN, MAIN_FONT, "CONGRATULATIONS! YOU WIN!")
            
            # Näytetään aika hieman alempana (y-akselin siirtymä)
            time_text = MAIN_FONT.render(f"Total time: {minutes}:{seconds:02d}", 1, (255, 255, 255))
            WIN.blit(time_text, (WIDTH//2 - time_text.get_width()//2, HEIGHT//2 + 50))
            
            restart_text = MAIN_FONT.render("Press any key to start over.", 1, (200, 200, 200))
            WIN.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 120))
            
            pygame.display.update()

            # Odotetaan pelaajan näppäinpainallusta (asynkronisesti)
            waiting = True
            while waiting:
                for event in pygame.event.get():
                    if event.type == pygame.KEYDOWN:
                        waiting = False
                    if event.type == pygame.QUIT:
                        run = False
                        waiting = False
                await asyncio.sleep(0) 

            # Nollataan peli
            g_info.reset()
            p_car.reset()
            c_car.reset()
            c_car.next_level(g_info.level)
        
        await asyncio.sleep(0)

    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())