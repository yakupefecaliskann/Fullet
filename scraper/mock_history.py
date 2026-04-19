import os
import random
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Starting to add mock history data...")

# Get all prices
res = supabase.table("fiyatlar").select("*").execute()
fiyatlar = res.data

# Clean old history
supabase.table("fiyat_gecmisi").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

changes = 0
for f in fiyatlar:
    # 20% chance to have a recent history change
    if random.random() < 0.20:
        istasyon_id = f["istasyon_id"]
        yakit = f["yakit_tipi"]
        suan_fiyat = f["fiyat"]
        
        # 50% discount, 50% increase
        if random.random() < 0.5:
            # Discount (eski fiyat is higher)
            eski_fiyat = suan_fiyat + round(random.uniform(0.15, 0.40), 2)
        else:
            # Increase (eski fiyat is lower)
            eski_fiyat = suan_fiyat - round(random.uniform(0.10, 0.50), 2)
            
        fiyat_farki = round(suan_fiyat - eski_fiyat, 2)
        
        supabase.table("fiyat_gecmisi").insert({
            "istasyon_id": istasyon_id,
            "yakit_tipi": yakit,
            "eski_fiyat": eski_fiyat,
            "yeni_fiyat": suan_fiyat,
            "fiyat_farki": fiyat_farki
        }).execute()
        changes += 1

print(f"Mocked {changes} price history records!")
