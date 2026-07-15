import type { VercelRequest, VercelResponse } from "@vercel/node";
import { Redis } from "@upstash/redis";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  try {
    if (req.method !== "POST") return res.status(405).end();

    const url = process.env.KV_REST_API_URL;
    const token = process.env.KV_REST_API_TOKEN;
    if (!url || !token) {
      return res.status(500).json({ error: "Missing KV env" });
    }

    const redis = new Redis({ url, token });

    const raw = req.body;
    const body = typeof raw === "string" ? JSON.parse(raw) : raw;
    const clientId = body?.clientId;

    if (!clientId) return res.status(400).json({ error: "clientId required" });

    const seenKey = `metrics:user_seen:${clientId}`;
    const first = await redis.set(seenKey, "1", {
      nx: true,
      ex: 60 * 60 * 24 * 365,
    });
    if (first) await redis.incr("metrics:users_total");

    return res.status(200).json({ ok: true, counted: Boolean(first) });
  } catch (e: any) {
    return res
      .status(500)
      .json({ error: "metrics-user failed", details: String(e?.message || e) });
  }
}
