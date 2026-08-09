import { Pool } from 'pg';

let pool: Pool | null = null;

function withNoVerifySsl(connectionString: string): string {
  const url = new URL(connectionString);
  url.searchParams.set('sslmode', 'no-verify');
  return url.toString();
}

export function getPool(): Pool {
  if (!pool) {
    // POSTGRES_URL (Vercel/Supabase integration) points at the Supavisor
    // pooler, which resolves over IPv4 — the direct DB_HOST is IPv6-only
    // and unreachable from Vercel's serverless runtime.
    pool = process.env.POSTGRES_URL
      ? new Pool({
          // pg-connection-string derives its ssl config from the URL's
          // sslmode and ignores a separate `ssl` option when connectionString
          // is set; Supabase's default sslmode=require ends up strict
          // (rejectUnauthorized=true) and rejects their cert as self-signed.
          connectionString: withNoVerifySsl(process.env.POSTGRES_URL),
          max: 5,
        })
      : new Pool({
          host: process.env.DB_HOST,
          port: Number(process.env.DB_PORT || 5432),
          database: process.env.DB_NAME,
          user: process.env.DB_USER,
          password: process.env.DB_PASSWORD,
          ssl: { rejectUnauthorized: false },
          max: 5,
        });
  }
  return pool;
}
