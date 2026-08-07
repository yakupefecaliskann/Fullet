const fs = require('fs');
const path = require('path');

const iconB64 = fs.readFileSync(
  'C:/Users/yefec/AppData/Local/Temp/claude/C--Fullet/11934d7d-72d9-4778-a6bc-9f50fa0452d6/scratchpad/icon_b64.txt',
  'utf8'
).trim();

const BG = '#0d2b26';
const BG2 = '#123a33';
const MINT = '#3ECF8E';
const WHITE = '#f3fbf8';
const RED = '#ff5a5a';
const BLUE = '#3b82f6';
const ORANGE = '#f5a524';

const base = (title, bodyHtml, accent) => `<!doctype html>
<html><head><meta charset="utf-8"><title>${title}</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  html,body { width:1080px; height:1350px; overflow:hidden; }
  body {
    font-family: 'Segoe UI', Arial, sans-serif;
    background: radial-gradient(circle at 50% -10%, ${BG2} 0%, ${BG} 55%);
    color: ${WHITE};
    position: relative;
  }
  .footer {
    position:absolute; left:0; right:0; bottom:0; height:170px;
    display:flex; align-items:center; padding:0 64px;
    border-top: 2px solid rgba(255,255,255,0.08);
  }
  .footer img { width:72px; height:72px; border-radius:18px; margin-right:24px; }
  .footer .brand { font-size:40px; font-weight:800; color:${WHITE}; }
  .footer .cta { margin-left:auto; background:${MINT}; color:${BG}; font-weight:800;
    font-size:28px; padding:16px 32px; border-radius:100px; }
  .pin { position:absolute; opacity:0.06; font-size:600px; right:-120px; bottom:60px; }
</style></head>
<body>
${bodyHtml}
<div class="footer">
  <img src="data:image/png;base64,${iconB64}" />
  <div class="brand">Fullet</div>
  <div class="cta">Ücretsiz İndir</div>
</div>
</body></html>`;

// ---------- 1. ZAM KARTI ----------
const zamBody = `
<div style="padding:72px 64px 0 64px;">
  <div style="display:inline-flex;align-items:center;gap:14px;background:rgba(255,90,90,0.15);
    border:2px solid ${RED};color:${RED};font-weight:800;font-size:30px;padding:14px 28px;
    border-radius:100px;">🔴 ZAM UYARISI</div>
  <div style="margin-top:56px;font-size:52px;font-weight:800;line-height:1.25;max-width:920px;">
    Bu gece 00:00'dan itibaren<br><span style="color:${MINT}">Motorin</span>e zam geliyor
  </div>
  <div style="margin-top:64px;display:flex;align-items:baseline;gap:20px;">
    <div style="font-size:180px;font-weight:900;color:${RED};line-height:1;">+1,42</div>
    <div style="font-size:56px;font-weight:800;color:${WHITE};">TL/L</div>
  </div>
  <div style="margin-top:48px;background:rgba(255,255,255,0.06);border-radius:24px;
    padding:36px 40px;font-size:34px;font-weight:600;max-width:880px;">
    60 litrelik depo için fark: <span style="color:${RED};font-weight:800;">+85 TL</span>
  </div>
  <div style="margin-top:48px;font-size:30px;color:rgba(243,251,248,0.75);max-width:760px;">
    Depon boşsa bu gece doldur. En yakın ve en ucuz istasyonu Fullet'te bul.
  </div>
</div>
<div class="pin">⛽</div>
`;

// ---------- 2. İL KARŞILAŞTIRMA KARTI ----------
const ilBody = `
<div style="padding:72px 64px 0 64px;">
  <div style="display:inline-flex;align-items:center;gap:14px;background:rgba(62,207,142,0.15);
    border:2px solid ${MINT};color:${MINT};font-weight:800;font-size:30px;padding:14px 28px;
    border-radius:100px;">📊 VERİ / İÇGÖRÜ</div>
  <div style="margin-top:56px;font-size:48px;font-weight:800;line-height:1.3;max-width:940px;">
    Aynı marka, iki ilçe:<br>litrede <span style="color:${MINT}">0,90 TL</span> fark
  </div>

  <div style="margin-top:70px;display:flex;gap:28px;">
    <div style="flex:1;background:rgba(255,255,255,0.06);border-radius:28px;padding:40px 32px;text-align:center;">
      <div style="font-size:30px;color:rgba(243,251,248,0.7);font-weight:600;">Kadıköy</div>
      <div style="font-size:72px;font-weight:900;margin-top:12px;">45,20</div>
      <div style="font-size:26px;color:rgba(243,251,248,0.5);">TL/L · Benzin</div>
    </div>
    <div style="display:flex;align-items:center;font-size:60px;color:${MINT};font-weight:900;">→</div>
    <div style="flex:1;background:rgba(255,255,255,0.06);border-radius:28px;padding:40px 32px;text-align:center;
      border:2px solid ${MINT};">
      <div style="font-size:30px;color:rgba(243,251,248,0.7);font-weight:600;">Beykoz</div>
      <div style="font-size:72px;font-weight:900;margin-top:12px;color:${MINT};">44,30</div>
      <div style="font-size:26px;color:rgba(243,251,248,0.5);">TL/L · Benzin</div>
    </div>
  </div>

  <div style="margin-top:56px;font-size:30px;color:rgba(243,251,248,0.75);max-width:800px;">
    Aynı şehirde bile fiyat farkı büyük olabiliyor. Fullet haritada anlık farkı gösterir.
  </div>
</div>
`;

// ---------- 3. EN UCUZ 5 KARTI ----------
const rows = [
  ['1', 'Opet', '44,10'],
  ['2', 'BP', '44,25'],
  ['3', 'Shell', '44,40'],
  ['4', 'Petrol Ofisi', '44,55'],
  ['5', 'Total', '44,60'],
];
const rankColor = (i) => (i === 0 ? MINT : i === 1 ? BLUE : i === 2 ? ORANGE : 'rgba(255,255,255,0.25)');
const listHtml = rows.map(([n, brand, price], i) => `
  <div style="display:flex;align-items:center;gap:28px;padding:22px 0;
    ${i < 4 ? 'border-bottom:1px solid rgba(255,255,255,0.08);' : ''}">
    <div style="width:56px;height:56px;border-radius:16px;background:${rankColor(i)};
      display:flex;align-items:center;justify-content:center;font-weight:900;font-size:30px;
      color:${i < 3 ? BG : WHITE};">${n}</div>
    <div style="font-size:36px;font-weight:700;flex:1;">${brand}</div>
    <div style="font-size:40px;font-weight:900;">${price} <span style="font-size:22px;font-weight:600;color:rgba(243,251,248,0.5);">TL/L</span></div>
  </div>`).join('');

const ucuzBody = `
<div style="padding:72px 64px 0 64px;">
  <div style="display:inline-flex;align-items:center;gap:14px;background:rgba(62,207,142,0.15);
    border:2px solid ${MINT};color:${MINT};font-weight:800;font-size:30px;padding:14px 28px;
    border-radius:100px;">⛽ EN UCUZ 5</div>
  <div style="margin-top:56px;font-size:52px;font-weight:800;line-height:1.25;max-width:900px;">
    Bugün <span style="color:${MINT}">İstanbul</span>'da<br>en ucuz 5 istasyon
  </div>
  <div style="margin-top:56px;background:rgba(255,255,255,0.05);border-radius:28px;padding:12px 40px;">
    ${listHtml}
  </div>
  <div style="margin-top:44px;font-size:30px;color:rgba(243,251,248,0.75);max-width:800px;">
    Liste her gün güncellenir. Kendi konumuna göre sıralamayı Fullet'te canlı gör.
  </div>
</div>
`;

const outDir = __dirname;
fs.writeFileSync(path.join(outDir, 'card_1_zam.html'), base('Zam Kartı', zamBody));
fs.writeFileSync(path.join(outDir, 'card_2_il_karsilastirma.html'), base('İl Karşılaştırma Kartı', ilBody));
fs.writeFileSync(path.join(outDir, 'card_3_en_ucuz_5.html'), base('En Ucuz 5 Kartı', ucuzBody));
console.log('3 HTML kart dosyası üretildi.');
