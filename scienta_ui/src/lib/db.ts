import { Pool } from "pg";
import { getRequiredEnv } from "@/lib/env";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

let pool: Pool | null = null;
let rootDatabaseUrlCache: string | null = null;

const PLACEHOLDER_PASSWORD_HASH =
  "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW";

async function ensureUsersPasswordHashColumn(p: Pool): Promise<void> {
  const tableExists = await p.query<{
    exists: boolean;
  }>(
    `SELECT EXISTS (
      SELECT 1
      FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name = 'users'
    )`
  );
  if (!tableExists.rows[0]?.exists) {
    return;
  }

  const columnExists = await p.query(
    `SELECT 1
     FROM information_schema.columns
     WHERE table_schema = 'public'
       AND table_name = 'users'
       AND column_name = 'password_hash'`
  );
  if (columnExists.rowCount) {
    return;
  }

  const client = await p.connect();
  try {
    await client.query("BEGIN");
    await client.query("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT");
    await client.query(
      `UPDATE users
       SET password_hash = $1
       WHERE password_hash IS NULL`,
      [PLACEHOLDER_PASSWORD_HASH]
    );
    await client.query("ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL");
    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

function getDatabaseUrl(): string {
  const fromProcess = process.env.DATABASE_URL?.trim();
  if (fromProcess) {
    return fromProcess;
  }
  if (rootDatabaseUrlCache !== null) {
    return rootDatabaseUrlCache;
  }

  const envCandidates = [
    path.resolve(process.cwd(), ".env"),
    path.resolve(process.cwd(), "scienta_ui", ".env"),
    path.resolve(process.cwd(), "..", ".env"),
  ];
  const envPath = envCandidates.find((candidate) => existsSync(candidate));
  if (!envPath) {
    rootDatabaseUrlCache = "";
    return getRequiredEnv("DATABASE_URL");
  }

  const rootEnv = readFileSync(envPath, "utf8");
  const match = rootEnv.match(/^DATABASE_URL=(.+)$/m);
  rootDatabaseUrlCache = match?.[1]?.trim().replace(/^['"]|['"]$/g, "") ?? "";
  if (!rootDatabaseUrlCache) {
    return getRequiredEnv("DATABASE_URL");
  }
  return rootDatabaseUrlCache;
}

export async function getPool(): Promise<Pool> {
  if (pool) {
    return pool;
  }
  pool = new Pool({
    connectionString: getDatabaseUrl(),
    max: 10,
  });
  await ensureUsersPasswordHashColumn(pool);
  return pool;
}
