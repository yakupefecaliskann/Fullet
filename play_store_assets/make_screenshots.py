from PIL import Image, ImageDraw, ImageFont
import os

# Yollar betiğin kendi konumuna göre çözülüyor. Eskiden eski proje dizini
# sabit yazılıydı; proje ASCII yol sorunu için `C:\Fullet`'e taşınınca
# (denetim bulgusu B1) betik sessizce hiçbir kaynağı bulamaz olmuştu — kaynak
# bulunamayınca çerçeve boş basılıyor, hata da vermiyor.
BASE   = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(BASE, 'source_screenshots')
OUTPUT = os.path.join(BASE, 'marketing')
os.makedirs(OUTPUT, exist_ok=True)

W, H = 1080, 1920

BG          = (12, 36, 16)
PHONE_BODY  = (14, 14, 14)
PHONE_BDR   = (52, 52, 52)
WHITE       = (255, 255, 255)
LIGHT_GREEN = (148, 218, 158)

PL, PR  = 165, 915
PT, PB  = 290, 1875
RADIUS  = 56
BEZEL   = 11

SL = PL + BEZEL
SR = PR - BEZEL
ST = PT + BEZEL + 32
SB = PB - BEZEL - 28

def find_font(names):
    for name in names:
        path = f'C:/Windows/Fonts/{name}'
        if os.path.exists(path):
            return path
    return None

BOLD = find_font(['segoeuib.ttf', 'arialbd.ttf', 'calibrib.ttf'])
REG  = find_font(['segoeui.ttf',  'arial.ttf',   'calibri.ttf'])

def make_screen(ss_file, line1, line2, subtitle, out_name):
    img = Image.new('RGB', (W, H), BG)
    d   = ImageDraw.Draw(img)

    fH = ImageFont.truetype(BOLD, 58)
    fS = ImageFont.truetype(REG,  37)

    # Phone body
    d.rounded_rectangle([PL, PT, PR, PB], radius=RADIUS,
                         fill=PHONE_BODY, outline=PHONE_BDR, width=3)

    # Notch
    nw = 158; nx = (W - nw) // 2
    d.rounded_rectangle([nx, PT+5, nx+nw, PT+33], radius=14, fill=PHONE_BODY)

    # Home bar
    hw = 108; hx = (W - hw) // 2
    d.rounded_rectangle([hx, PB-22, hx+hw, PB-16], radius=4, fill=(72, 72, 72))

    # Screenshot
    ss_path = os.path.join(SOURCE, ss_file)
    if os.path.exists(ss_path):
        ss = Image.open(ss_path).convert('RGB')
        sw, sh = SR - SL, SB - ST
        r_ss = ss.width / ss.height
        r_sc = sw / sh
        if r_ss > r_sc:
            nw2 = int(sh * r_ss); nh2 = sh
        else:
            nw2 = sw; nh2 = int(sw / r_ss)
        ss2 = ss.resize((nw2, nh2), Image.LANCZOS)
        cx = (nw2 - sw) // 2; cy = (nh2 - sh) // 2
        ss3 = ss2.crop((cx, cy, cx+sw, cy+sh))

        mask = Image.new('L', (sw, sh), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, sw, sh], radius=max(0, RADIUS - BEZEL - 4), fill=255)
        img.paste(ss3, (SL, ST), mask)

    # Centered text helper
    def ctext(text, font, y, color):
        bb = d.textbbox((0, 0), text, font=font)
        x  = (W - (bb[2] - bb[0])) // 2
        d.text((x, y), text, font=font, fill=color)

    ctext(line1,   fH, 60,  WHITE)
    ctext(line2,   fH, 138, WHITE)
    ctext(subtitle, fS, 224, LIGHT_GREEN)

    out = os.path.join(OUTPUT, f'{out_name}.png')
    img.save(out)
    print(f'OK  {out_name}.png')


screens = [
    ('ss_47.jpeg',
     'Tüm İstanbul,', 'tüm istasyonlar',
     '1.800+ istasyon · Benzin · Motorin · LPG · Şarj',
     '01_harita_genel'),

    ('ss_52.jpeg',
     'Yakındaki fiyatı', 'anında gör',
     'Sürüş takibi açık · Opet 0.7 km · 63,08 TL',
     '02_fiyat_harita'),

    ('ss_44.jpeg',
     'Fiyatı gör,', 'tek tuşla yola çık',
     'Benzin · Motorin · LPG · Şarj',
     '03_istasyon_detay'),

    ('ss_45.jpeg',
     'Dolum maliyetini', 'önceden bil',
     '50 L × 63,08 ₺ = hesabını çıkar',
     '04_depo_hesabi'),

    ('ss_50.jpeg',
     'Akıllı sıralama', 'ile doğru seçim',
     'Mesafe + fiyat dengesi, senin için',
     '05_akilli_mod'),

    ('ss_51.jpeg',
     'Gece modu', 'dahil',
     'Göz yormayan karanlık tema',
     '06_gece_modu'),
]

for args in screens:
    make_screen(*args)

print('\nTamamlandı! 6 marketing screenshot hazır.')
print(f'Konum: {OUTPUT}')
