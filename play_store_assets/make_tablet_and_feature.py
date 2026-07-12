from PIL import Image, ImageDraw, ImageFont
import os

SOURCE  = r'C:\Users\yefec\Desktop\Fullet\play_store_assets\source_screenshots'
MKTG    = r'C:\Users\yefec\Desktop\Fullet\play_store_assets\marketing'
OUT7    = os.path.join(MKTG, 'tablet7')
OUT10   = os.path.join(MKTG, 'tablet10')
for d in [OUT7, OUT10]: os.makedirs(d, exist_ok=True)

BG          = (12, 36, 16)
PHONE_BODY  = (14, 14, 14)
PHONE_BDR   = (52, 52, 52)
WHITE       = (255, 255, 255)
LIGHT_GREEN = (148, 218, 158)
CHIP_GREEN  = (32, 140, 74)
CHIP_BLUE   = (30, 100, 175)
CHIP_AMBER  = (180, 100, 20)

def find_font(names):
    for n in names:
        p = f'C:/Windows/Fonts/{n}'
        if os.path.exists(p): return p
    return None

BOLD = find_font(['segoeuib.ttf', 'arialbd.ttf', 'calibrib.ttf'])
REG  = find_font(['segoeui.ttf',  'arial.ttf',   'calibri.ttf'])

# ─── TABLET SCREENSHOT ──────────────────────────────────────────────────────

def make_tablet(ss_file, line1, line2, subtitle, out_path, W, H):
    fs = W / 1080.0          # font scale relative to phone canvas

    PW  = int(W * 0.67)      # phone width = 67% of canvas
    PL  = (W - PW) // 2
    PR  = PL + PW
    PT  = int(H * 0.145)
    PB  = int(H * 0.975)
    RAD = int(PW * 0.075)
    BEV = int(PW * 0.015)

    SL = PL + BEV;  SR = PR - BEV
    ST = PT + BEV + int(PW * 0.043)
    SB = PB - BEV - int(PW * 0.038)

    img = Image.new('RGB', (W, H), BG)
    d   = ImageDraw.Draw(img)

    fH = ImageFont.truetype(BOLD, int(58 * fs))
    fS = ImageFont.truetype(REG,  int(37 * fs))

    # Phone body
    d.rounded_rectangle([PL, PT, PR, PB], radius=RAD,
                         fill=PHONE_BODY, outline=PHONE_BDR, width=max(2, int(3*fs)))
    # Notch
    nw = int(PW * 0.21); nx = (W - nw) // 2
    d.rounded_rectangle([nx, PT+max(4,int(5*fs)), nx+nw, PT+int(RAD*0.58)],
                         radius=int(14*fs), fill=PHONE_BODY)
    # Home bar
    hw = int(PW * 0.15); hx = (W - hw) // 2
    d.rounded_rectangle([hx, PB-int(22*fs), hx+hw, PB-int(16*fs)],
                         radius=int(4*fs), fill=(72,72,72))

    # Screenshot
    ss_path = os.path.join(SOURCE, ss_file)
    if os.path.exists(ss_path):
        ss = Image.open(ss_path).convert('RGB')
        sw, sh = SR-SL, SB-ST
        r_ss, r_sc = ss.width/ss.height, sw/sh
        if r_ss > r_sc: nw2=int(sh*r_ss); nh2=sh
        else:           nw2=sw;           nh2=int(sw/r_ss)
        ss2 = ss.resize((nw2, nh2), Image.LANCZOS)
        cx=(nw2-sw)//2; cy=(nh2-sh)//2
        ss3 = ss2.crop((cx, cy, cx+sw, cy+sh))
        mask = Image.new('L', (sw, sh), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0,0,sw,sh], radius=max(0,RAD-BEV-4), fill=255)
        img.paste(ss3, (SL, ST), mask)

    # Text
    def ctext(text, font, y, color):
        bb = d.textbbox((0,0), text, font=font)
        d.text(((W-(bb[2]-bb[0]))//2, y), text, font=font, fill=color)

    ty0 = int(H * 0.025)
    lg  = int(H * 0.043)
    ctext(line1,    fH, ty0,          WHITE)
    ctext(line2,    fH, ty0+lg,       WHITE)
    ctext(subtitle, fS, ty0+int(2.3*lg), LIGHT_GREEN)

    img.save(out_path)
    print(f'  OK  {os.path.basename(out_path)}')


SCREENS = [
    ('ss_47.jpeg',  'Tüm İstanbul,',    'tüm istasyonlar',  '1.800+ istasyon · Anlık güncelleme',       '01_harita_genel.png'),
    ('ss_52.jpeg',  'Yakındaki fiyatı', 'anında gör',       'Sürüş takibi açık · 0.7 km · 63,08 TL',   '02_fiyat_harita.png'),
    ('ss_44.jpeg',  'Fiyatı gör,',      'tek tuşla yola çık','Benzin · Motorin · LPG · Şarj',           '03_istasyon_detay.png'),
    ('ss_45.jpeg',  'Dolum maliyetini', 'önceden bil',      '50 L × 63,08 ₺ = hesabını çıkar',          '04_depo_hesabi.png'),
    ('ss_50.jpeg',  'Akıllı sıralama',  'ile doğru seçim',  'Mesafe + fiyat dengesi, senin için',        '05_akilli_mod.png'),
    ('ss_51.jpeg',  'Gece modu',        'dahil',            'Göz yormayan karanlık tema',                '06_gece_modu.png'),
]

print('\n7" tablet (1200×1920)...')
for ss, l1, l2, sub, fn in SCREENS:
    make_tablet(ss, l1, l2, sub, os.path.join(OUT7, fn),  1200, 1920)

print('\n10" tablet (1600×2560)...')
for ss, l1, l2, sub, fn in SCREENS:
    make_tablet(ss, l1, l2, sub, os.path.join(OUT10, fn), 1600, 2560)


# ─── FEATURE GRAPHIC 1024×500 ───────────────────────────────────────────────

def make_feature_graphic():
    W, H = 1024, 500
    img = Image.new('RGB', (W, H), BG)
    d   = ImageDraw.Draw(img)

    fTitle   = ImageFont.truetype(BOLD, 66)
    fTagline = ImageFont.truetype(REG,  29)
    fDesc    = ImageFont.truetype(REG,  22)
    fChip    = ImageFont.truetype(BOLD, 21)

    # ── Right side: phone mockup ──────────────────────────────────────────
    phone_src = os.path.join(SOURCE, 'ss_52.jpeg')
    if os.path.exists(phone_src):
        ss = Image.open(phone_src).convert('RGB')

        # Phone frame canvas (portrait, fits into ~480×H area on the right)
        PH = H + 60           # slightly taller than canvas → crops top/bottom
        PW = int(PH * 0.475)  # realistic phone ratio
        frame = Image.new('RGB', (PW, PH), BG)
        fd    = ImageDraw.Draw(frame)
        RAD   = int(PW * 0.075)
        BEV   = 10

        fd.rounded_rectangle([0, 0, PW, PH], radius=RAD,
                               fill=PHONE_BODY, outline=PHONE_BDR, width=3)

        # Notch
        nw = int(PW * 0.22); nx = (PW - nw) // 2
        fd.rounded_rectangle([nx, 4, nx+nw, 32], radius=12, fill=PHONE_BODY)

        # Home bar
        hw = int(PW * 0.16); hx = (PW - hw) // 2
        fd.rounded_rectangle([hx, PH-20, hx+hw, PH-14], radius=4, fill=(72,72,72))

        # Screenshot inside
        SL2=BEV; SR2=PW-BEV; ST2=BEV+28; SB2=PH-BEV-22
        sw,sh = SR2-SL2, SB2-ST2
        r_ss,r_sc = ss.width/ss.height, sw/sh
        if r_ss>r_sc: nw2=int(sh*r_ss); nh2=sh
        else:         nw2=sw;           nh2=int(sw/r_ss)
        ss2 = ss.resize((nw2,nh2), Image.LANCZOS)
        cx=(nw2-sw)//2; cy=(nh2-sh)//2
        ss3 = ss2.crop((cx,cy,cx+sw,cy+sh))
        mask=Image.new('L',(sw,sh),0)
        ImageDraw.Draw(mask).rounded_rectangle([0,0,sw,sh], radius=max(0,RAD-BEV-2), fill=255)
        frame.paste(ss3,(SL2,ST2),mask)

        # Paste phone onto canvas (right side, vertically centered + slight overflow)
        px = W - PW + 10
        py = (H - PH) // 2
        img.paste(frame, (px, py))

    # ── Left side: icon + text ────────────────────────────────────────────
    icon_path = r'C:\Users\yefec\Desktop\Fullet\play_store_assets\upload\app_icon_512.png'
    icon_x, icon_y, icon_size = 55, 55, 88
    if os.path.exists(icon_path):
        icon = Image.open(icon_path).convert('RGBA')
        icon = icon.resize((icon_size, icon_size), Image.LANCZOS)
        icon_mask = Image.new('L', (icon_size, icon_size), 0)
        ImageDraw.Draw(icon_mask).rounded_rectangle([0,0,icon_size,icon_size], radius=20, fill=255)
        img.paste(icon, (icon_x, icon_y), icon_mask)
    else:
        d.rounded_rectangle([icon_x, icon_y, icon_x+icon_size, icon_y+icon_size],
                              radius=20, fill=(30,120,70))

    # "Fullet" title
    d.text((icon_x + icon_size + 20, icon_y + 8), 'Fullet', font=fTitle, fill=WHITE)

    # Tagline
    d.text((icon_x, icon_y + icon_size + 22), 'Yakıt fiyatları haritada', font=fTagline, fill=LIGHT_GREEN)

    # Description
    d.text((icon_x, icon_y + icon_size + 68), 'En yakın istasyon. Güncel fiyat. Hızlı rota.', font=fDesc, fill=(190,215,192))

    # Chips
    chips = [('Benzin', CHIP_GREEN), ('Motorin', CHIP_BLUE), ('LPG', CHIP_AMBER)]
    cx2 = icon_x
    cy2 = icon_y + icon_size + 114
    for label, color in chips:
        bb = d.textbbox((0,0), label, font=fChip)
        tw = bb[2]-bb[0]
        pw2 = tw + 36
        ph2 = 36
        d.rounded_rectangle([cx2, cy2, cx2+pw2, cy2+ph2], radius=18, fill=color)
        d.text((cx2+18, cy2+8), label, font=fChip, fill=WHITE)
        cx2 += pw2 + 12

    out = os.path.join(MKTG, 'feature_graphic_1024x500_new.png')
    img.save(out)
    print(f'\n  OK  feature_graphic_1024x500_new.png')


print('\nÖzellik grafiği (1024×500)...')
make_feature_graphic()

print('\nTümü tamamlandı!')
print(f'  7"  tablet  → {OUT7}')
print(f'  10" tablet  → {OUT10}')
print(f'  Feature     → {MKTG}\\feature_graphic_1024x500_new.png')
