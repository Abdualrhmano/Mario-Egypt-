import pygame, sys, random, requests

pygame.init()
WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("King Khufu Adventure")

# إعدادات اللاعب
player = pygame.Rect(100, 600, 50, 50)
velocity_y = 0
gravity = 1
jump = -18

# بيانات اللاعب
username = "Player1"
coins = 0
abilities = {"double_jump": False, "shield": False, "magic": False}
current_level = 0

# المستويات (40 مستوى)
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

# أعداء لكل مستوى
def generate_enemies(level):
    enemies = []
    for i in range(level + 2):
        enemies.append(pygame.Rect(random.randint(200, WIDTH-50), 600, 50, 50))
    return enemies

enemies = generate_enemies(current_level)
clock = pygame.time.Clock()

# شاشة تأكيد الدفع
def payment_confirmation(expiry_date):
    font = pygame.font.SysFont("Arial", 40)
    while True:
        screen.fill((0, 0, 0))
        msg = font.render("✅ تم الاشتراك بنجاح", True, (0, 255, 0))
        expiry = font.render(f"الاشتراك فعال حتى: {expiry_date}", True, (255, 255, 255))
        cont = font.render("اضغط أي مفتاح للمتابعة", True, (255, 215, 0))
        screen.blit(msg, (WIDTH//2 - 200, 250))
        screen.blit(expiry, (WIDTH//2 - 250, 350))
        screen.blit(cont, (WIDTH//2 - 250, 450))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN: return "done"

# شاشة الاشتراك
def subscription_screen():
    font = pygame.font.SysFont("Arial", 40)
    input_box = pygame.Rect(WIDTH//2 - 150, 300, 300, 50)
    color_inactive = pygame.Color('lightskyblue3')
    color_active = pygame.Color('dodgerblue2')
    color = color_inactive
    active = False
    text = ''
    message = ''
    while True:
        screen.fill((0, 0, 0))
        title = font.render("اشتراك شهري - فودافون كاش", True, (255, 215, 0))
        screen.blit(title, (WIDTH//2 - 250, 150))
        txt_surface = font.render(text, True, color)
        width = max(300, txt_surface.get_width()+10)
        input_box.w = width
        screen.blit(txt_surface, (input_box.x+5, input_box.y+5))
        pygame.draw.rect(screen, color, input_box, 2)
        pay_button = font.render("اضغط للدفع", True, (255,255,255))
        screen.blit(pay_button, (WIDTH//2 - 100, 400))
        msg_surface = font.render(message, True, (255, 0, 0))
        screen.blit(msg_surface, (WIDTH//2 - 200, 500))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos): active = not active
                else: active = False
                color = color_active if active else color_inactive
                if WIDTH//2 - 100 < event.pos[0] < WIDTH//2+100 and 400 < event.pos[1] < 450:
                    try:
                        response = requests.post("http://localhost:8000/pay", json={"phone_number": text,"amount": 3.0})
                        if response.status_code == 200:
                            data = response.json()
                            expiry_date = data.get("details", {}).get("expiry", "غير محدد")
                            return payment_confirmation(expiry_date)
                        else: message = "فشل الاتصال بالسيرفر ❌"
                    except Exception as e: message = f"خطأ: {e}"
            if event.type == pygame.KEYDOWN:
                if active:
                    if event.key == pygame.K_RETURN:
                        try:
                            response = requests.post("http://localhost:8000/pay", json={"phone_number": text,"amount": 3.0})
                            if response.status_code == 200:
                                data = response.json()
                                expiry_date = data.get("details", {}).get("expiry", "غير محدد")
                                return payment_confirmation(expiry_date)
                            else: message = "فشل الاتصال بالسيرفر ❌"
                        except Exception as e: message = f"خطأ: {e}"
                    elif event.key == pygame.K_BACKSPACE: text = text[:-1]
                    else: text += event.unicode

# شاشة المتجر
def shop_screen():
    global coins, abilities
    font = pygame.font.SysFont("Arial", 40)
    while True:
        screen.fill((0, 0, 0))
        title = font.render("🏺 متجر القدرات", True, (255, 215, 0))
        balance = font.render(f"عملاتك: {coins}", True, (255, 255, 255))
        option1 = font.render("1. قفزة مزدوجة (10)", True, (255,255,255))
        option2 = font.render("2. درع حماية (15)", True, (255,255,255))
        option3 = font.render("3. سحر فرعوني (20)", True, (255,255,255))
        back = font.render("4. رجوع", True, (255,255,255))
        screen.blit(title, (WIDTH//2 - 150, 100))
        screen.blit(balance, (WIDTH//2 - 150, 180))
        screen.blit(option1, (WIDTH//2 - 200, 250))
        screen.blit(option2, (WIDTH//2 - 200, 320))
        screen.blit(option3, (WIDTH//2 - 200, 390))
        screen.blit(back, (WIDTH//2 - 200, 460))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1 and coins >= 10: abilities["double_jump"]=True; coins-=10
                elif event.key == pygame.K_2 and coins >= 15: abilities["shield"]=True; coins-=15
                elif event.key == pygame.K_3 and coins >= 20: abilities["magic"]=True; coins-=20
                elif event.key == pygame.K_4: return

# شاشة المتصدرين
def leaderboard_screen():
    font = pygame.font.SysFont("Arial", 40)
    try:
        response = requests.get("http://localhost:8000/leaderboard")
        if response.status_code == 200: leaderboard = response.json().get("top_players", [])
        else: leaderboard = []
    except: leaderboard = []
    while True:
        screen.fill((0, 0, 0))
        title = font.render("🏆 لوحة المتصدرين", True, (255, 215, 0))
        screen.blit(title, (WIDTH//2 - 150, 100))
        y_offset = 200
        for i, player_data in enumerate(leaderboard):
            line = font.render(f"{i+1}. {player_data['username']} - {player_data['coins']} عملة - مستوى {player_data['level']}", True, (255,255,255))
            screen.blit(line, (WIDTH//2 - 300, y_offset))
            y_offset += 50
        back = font
