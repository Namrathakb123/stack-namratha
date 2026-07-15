import type { VercelRequest, VercelResponse } from "@vercel/node";
import { Redis } from "@upstash/redis";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  try {
    if (req.method !== "GET") return res.status(405).end();

    const url = process.env.KV_REST_API_URL;
    const token = process.env.KV_REST_API_TOKEN;
    if (!url || !token) {
      return res.status(500).json({ error: "Missing KV env" });
    }

    const redis = new Redis({ url, token });

    const [usersTotal, pdfsTotal] = await Promise.all([
      redis.get<number>("metrics:users_total"),
      redis.get<number>("metrics:pdfs_total"),
    ]);

    return res
      .status(200)
      .json({ usersTotal: usersTotal ?? 0, pdfsTotal: pdfsTotal ?? 0 });
  } catch (e: any) {
    return res
      .status(500)
      .json({ error: "metrics failed", details: String(e?.message || e) });
  }
}
