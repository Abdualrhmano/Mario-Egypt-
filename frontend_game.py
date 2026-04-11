import pygame
import sys
import random
import warnings
import os

# 1. حل مشكلة التحذيرات (Warnings) التي تظهر في الـ Terminal
warnings.filterwarnings("ignore", category=DeprecationWarning)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# تهيئة Pygame
pygame.init()

# الإعدادات الأساسية
WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("King Khufu Adventure - مغامرة الملك خوفو")
clock = pygame.time.Clock()

# الألوان
WHITE = (255, 255, 255)
GOLD = (255, 215, 0)
BLACK = (0, 0, 0)
SKY_BLUE = (135, 206, 235)
SAND = (194, 178, 128)

# إعدادات اللاعب
player = pygame.Rect(100, 600, 50, 50)
velocity_y = 0
gravity = 1
jump = -18

# بيانات اللاعب والتقدم
username = "Player1"
coins = 0
abilities = {"double_jump": False, "shield": False, "magic": False}
current_level = 0

# قائمة المستويات (40 مستوى)
levels = [
    "الأهرامات","أبو الهول","النيل","الأقصر","الكرنك",
    "الصحراء الغربية","واحة سيوة","مقابر الملوك","كنوز توت عنخ آمون","المتحف المصري",
    "جزيرة فيلة","أسوان","حتشبسوت","وادي الملوك","إدفو",
    "دندرة","كوم أمبو","أبيدوس","أبو سمبل","طيبة",
    "معبد الشمس","بحيرة الكرستال","غابة البردي","مدينة هليوبوليس","ممر الرمال المتحركة",
    "معبد رع","وادي العقارب","قصر الملكة نفرتيتي","المتحف السري","معبد حورس",
    "جزيرة النخيل","معبد أنوبيس","وادي الذهب","مدينة ممفيس","معبد بتاح",
    "الصحراء الكبرى","واحة الفيوم","معبد إيزيس","قصر الفرعون الأخير","العاصمة السرية"
]

def generate_enemies(level):
    new_enemies = []
    # زيادة عدد الأعداء مع زيادة المستوى
    for i in range(min(level + 2, 8)): 
        new_enemies.append(pygame.Rect(random.randint(400, WIDTH-50), 600, 50, 50))
    return new_enemies

enemies = generate_enemies(current_level)

# --- الشاشات المساعدة ---

def payment_confirmation(expiry_date):
    font = pygame.font.SysFont("Arial", 40)
    while True:
        screen.fill(BLACK)
        msg = font.render("✅ تم الاشتراك بنجاح", True, (0, 255, 0))
        expiry = font.render(f"الاشتراك فعال حتى: {expiry_date}", True, WHITE)
        cont = font.render("اضغط أي مفتاح للمتابعة", True, GOLD)
        screen.blit(msg, (WIDTH//2-200, 250))
        screen.blit(expiry, (WIDTH//2-250, 350))
        screen.blit(cont, (WIDTH//2-200, 450))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN: return "done"

def subscription_screen():
    font = pygame.font.SysFont("Arial", 40)
    input_box = pygame.Rect(WIDTH//2-150, 300, 300, 50)
    color_inactive = pygame.Color('lightskyblue3')
    color_active = pygame.Color('dodgerblue2')
    color = color_inactive
    active = False
    text = ''
    while True:
        screen.fill(BLACK)
        title = font.render("اشتراك شهري - فودافون كاش", True, GOLD)
        screen.blit(title, (WIDTH//2-250, 150))
        
        txt_surface = font.render(text, True, color)
        pygame.draw.rect(screen, color, input_box, 2)
        screen.blit(txt_surface, (input_box.x+5, input_box.y+5))
        
        pay_btn = font.render("اضغط هنا للدفع (محاكاة)", True, WHITE)
        screen.blit(pay_btn, (WIDTH//2-150, 450))
        
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos): active = not active
                else: active = False
                color = color_active if active else color_inactive
                # محاكاة الضغط على زر الدفع
                if 450 < event.pos[1] < 500: return payment_confirmation("2026-05-11")
            if event.type == pygame.KEYDOWN:
                if active:
                    if event.key == pygame.K_RETURN: return payment_confirmation("2026-05-11")
                    elif event.key == pygame.K_BACKSPACE: text = text[:-1]
                    else: text += event.unicode
                if event.key == pygame.K_ESCAPE: return

def shop_screen():
    global coins, abilities
    font = pygame.font.SysFont("Arial", 40)
    while True:
        screen.fill(BLACK)
        title = font.render("🏺 متجر القدرات الفرعونية", True, GOLD)
        balance = font.render(f"عملاتك الحالية: {coins}", True, WHITE)
        s1 = font.render("1. قفزة مزدوجة (10 عملات)", True, WHITE)
        s2 = font.render("2. درع حماية (15 عملة)", True, WHITE)
        back = font.render("ESC. للرجوع", True, GOLD)
        
        screen.blit(title, (WIDTH//2-180, 100))
        screen.blit(balance, (WIDTH//2-150, 180))
        screen.blit(s1, (WIDTH//2-200, 280))
        screen.blit(s2, (WIDTH//2-200, 350))
        screen.blit(back, (WIDTH//2-100, 500))
        
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1 and coins >= 10: 
                    abilities["double_jump"] = True; coins -= 10
                elif event.key == pygame.K_2 and coins >= 15: 
                    abilities["shield"] = True; coins -= 15
                elif event.key == pygame.K_ESCAPE: return

def leaderboard_screen():
    font = pygame.font.SysFont("Arial", 40)
    data = [{"n": "Khufu_King", "c": 150, "l": 25}, {"n": "Osiris", "c": 90, "l": 12}]
    while True:
        screen.fill(BLACK)
        title = font.render("🏆 قائمة المتصدرين", True, GOLD)
        screen.blit(title, (WIDTH//2-150, 80))
        y = 200
        for item in data:
            txt = font.render(f"{item['n']} - Level: {item['l']} - Coins: {item['c']}", True, WHITE)
            screen.blit(txt, (WIDTH//2-250, y))
            y += 60
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN: return

# --- المحرك الأساسي للعبة ---

def start_game():
    global velocity_y, coins, current_level, enemies
    player.x = 100
    running = True
    while running:
        screen.fill(SKY_BLUE)
        pygame.draw.rect(screen, SAND, (0, 650, WIDTH, 50)) # الأرضية
        
        # عرض معلومات المستوى
        font = pygame.font.SysFont("Arial", 30)
        info = font.render(f"المكان: {levels[current_level]} | العملات: {coins}", True, BLACK)
        screen.blit(info, (20, 20))
        
        # رسم اللاعب
        pygame.draw.rect(screen, (150, 75, 0), player) # لون بني بسيط للخوفو
        
        # حركة ومعالجة الأعداء
        for enemy in enemies:
            pygame.draw.rect(screen, (50, 50, 50), enemy)
            enemy.x -= (5 + current_level // 5) # تزيد السرعة مع المستويات
            if enemy.x < -50: enemy.x = WIDTH + random.randint(100, 500)
            
            if player.colliderect(enemy):
                if abilities["shield"]:
                    abilities["shield"] = False
                    enemy.x = -100 # إبعاد العدو
                else:
                    return "game_over"

        # فيزياء الجاذبية
        velocity_y += gravity
        player.y += velocity_y
        if player.y >= 600:
            player.y = 600
            velocity_y = 0
            
        # الانتقال للمستوى التالي
        if player.x > WIDTH:
            current_level = (current_level + 1) % len(levels)
            coins += 5
            player.x = 50
            enemies = generate_enemies(current_level)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and player.y == 600:
                    velocity_y = jump
                elif event.key == pygame.K_RIGHT: player.x += 25
                elif event.key == pygame.K_LEFT: player.x -= 25

        pygame.display.flip()
        clock.tick(60)

# القائمة الرئيسية
def main_menu():
    font = pygame.font.SysFont("Arial", 50)
    while True:
        screen.fill(BLACK)
        title = font.render("King Khufu Adventure", True, GOLD)
        screen.blit(title, (WIDTH//2-250, 100))
        options = ["1. ابدأ المغامرة", "2. اشتراك فودافون كاش", "3. المتجر", "4. المتصدرين", "5. خروج"]
        for i, opt in enumerate(options):
            txt = font.render(opt, True, WHITE)
            screen.blit(txt, (WIDTH//2-180, 220 + i*70))
        
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: return "start"
                if event.key == pygame.K_2: subscription_screen()
                if event.key == pygame.K_3: shop_screen()
                if event.key == pygame.K_4: leaderboard_screen()
                if event.key == pygame.K_5: pygame.quit(); sys.exit()

# تشغيل التطبيق
if __name__ == "__main__":
    while True:
        action = main_menu()
        if action == "start":
            res = start_game()
            if res == "game_over":
                current_level = 0
                # شاشة خسارة سريعة
                screen.fill((200, 0, 0))
                f = pygame.font.SysFont("Arial", 60)
                screen.blit(f.render("GAME OVER", True, WHITE), (WIDTH//2-150, HEIGHT//2))
                pygame.display.flip()
                pygame.time.delay(2000)
