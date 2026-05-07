import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.7.1";

type PushToken = {
  token: string;
  provider?: string | null;
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

function isAuthorized(req: Request) {
  const authHeader = req.headers.get("Authorization") ?? "";
  const token = authHeader.replace(/^Bearer\s+/i, "");
  const expectedToken = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  return Boolean(expectedToken && token && token === expectedToken);
}

function chunks<T>(items: T[], size: number) {
  const result: T[][] = [];
  for (let index = 0; index < items.length; index += size) {
    result.push(items.slice(index, index + size));
  }
  return result;
}

async function sendExpo(tokens: string[], title: string, body: string) {
  let delivered = 0;
  for (const chunk of chunks(tokens, 100)) {
    const response = await fetch("https://exp.host/--/api/v2/push/send", {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(
        chunk.map((token) => ({
          to: token,
          sound: "default",
          title,
          body,
          data: { route: "home" },
        })),
      ),
    });
    if (response.ok) delivered += chunk.length;
  }
  return delivered;
}

serve(async (req) => {
  if (req.method !== "POST") {
    return json({ error: "Method not allowed" }, 405);
  }

  if (!isAuthorized(req)) {
    return json({ error: "Unauthorized" }, 401);
  }

  try {
    const payload = await req.json();
    if (payload?.action !== "SUMMARY_PUSH") {
      return json({ error: "Unknown action" }, 400);
    }

    const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
    const supabase = createClient(supabaseUrl, serviceKey);

    const { data, error } = await supabase
      .from("push_tokens")
      .select("token, provider");

    if (error) {
      return json({ error: error.message }, 500);
    }

    const tokens = (data ?? []) as PushToken[];
    const title = payload.isZam
      ? "Akaryakit fiyat uyarisi"
      : "Akaryakit fiyatlari guncellendi";
    const body = String(payload.message ?? "Fullet verileri guncellendi.").slice(0, 240);

    const expoTokens = tokens
      .filter((item) => item.provider === "expo" || item.token.includes("ExpoPushToken") || item.token.includes("ExponentPushToken"))
      .map((item) => item.token);

    const deliveredExpo = expoTokens.length > 0
      ? await sendExpo(expoTokens, title, body)
      : 0;

    const fcmTokens = tokens.filter((item) => item.provider === "fcm").length;

    return json({
      status: "ok",
      deliveredExpo,
      pendingFcm: fcmTokens,
      note: fcmTokens > 0
        ? "FCM HTTP v1 service account is not configured in this edge function yet."
        : undefined,
    });
  } catch (err) {
    return json({ error: err instanceof Error ? err.message : String(err) }, 500);
  }
});
