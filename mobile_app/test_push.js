const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = 'https://xhkvlwecsacfjpbtyqcc.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhoa3Zsd2Vjc2FjZmpwYnR5cWNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY0ODQwNzEsImV4cCI6MjA5MjA2MDA3MX0.vxukykdKD5384K1Pm3TRu5sP-BpgQ0SXGEGildObSbk';
const supabase = createClient(supabaseUrl, supabaseKey);

async function testPush() {
  console.log("Supabase'den tokenler cekiliyor...");
  const { data, error } = await supabase.from('push_tokens').select('token');
  
  if (error) {
    console.error("Supabase Hatasi:", error);
    return;
  }
  if (!data || data.length === 0) {
    console.log("Hic kayitli cihaz (token) bulunamadi. Lutfen uygulamayi telefonunda acip (Expo Go) Bildirim Iznine 'Evet' de.");
    return;
  }

  console.log(`${data.length} adet cihaza bildirim yollaniyor...`);

  const messages = data.map(item => ({
    to: item.token,
    sound: 'default',
    title: '🚨 FULLET ZAM ALARMI!',
    body: 'Kanka! Bu gece yarısından itibaren Benzine 1.45 TL zam bekleniyor. Ucuz istasyonları Garajına göre haritandan kontrol et, kuyruk başlamadan Fullet! 🚀',
    data: { action: 'open_map' },
  }));

  try {
    const response = await fetch('https://exp.host/--/api/v2/push/send', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Accept-encoding': 'gzip, deflate',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(messages),
    });
    console.log("Bildirim Gonderim Sonucu (Durum): ", response.status);
    console.log(await response.json());
    console.log("✅ Bildirim basariyla ateslendi!");
  } catch(err) {
    console.error("Gonderim hatasi:", err);
  }
}

testPush();
