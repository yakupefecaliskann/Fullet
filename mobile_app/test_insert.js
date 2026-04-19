const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = 'https://xhkvlwecsacfjpbtyqcc.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhoa3Zsd2Vjc2FjZmpwYnR5cWNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY0ODQwNzEsImV4cCI6MjA5MjA2MDA3MX0.vxukykdKD5384K1Pm3TRu5sP-BpgQ0SXGEGildObSbk';
const supabase = createClient(supabaseUrl, supabaseKey);

async function testInsert() {
  const testToken = "ExponentPushToken[TestAbc123]";
  console.log("Mock token ekleniyor...");
  const { data, error } = await supabase.from('push_tokens').insert([{ token: testToken }]).select();
  
  if (error) {
    console.error("Supabase Insert Hatasi (Buyuk ihtimalle RLS veya Tablo yapisi!):", error);
  } else {
    console.log("Insert Basarili. Eklenen Data:", data);
  }
}

testInsert();
