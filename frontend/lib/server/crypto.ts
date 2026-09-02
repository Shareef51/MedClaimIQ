import "server-only";
import { createCipheriv, createDecipheriv, createHash, randomBytes } from "node:crypto";
import { serverEnv } from "./env";

const VERSION = "v1";

function key(): Buffer {
  return createHash("sha256").update(serverEnv.sessionSecret(), "utf8").digest();
}

function b64url(value: Buffer): string {
  return value.toString("base64url");
}

export function seal<T>(payload: T): string {
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key(), iv);
  const plaintext = Buffer.from(JSON.stringify(payload), "utf8");
  const encrypted = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  const tag = cipher.getAuthTag();
  return [VERSION, b64url(iv), b64url(tag), b64url(encrypted)].join(".");
}

export function unseal<T>(sealed: string | undefined | null): T | null {
  if (!sealed) return null;
  try {
    const [version, ivRaw, tagRaw, bodyRaw] = sealed.split(".");
    if (version !== VERSION || !ivRaw || !tagRaw || !bodyRaw) return null;
    const decipher = createDecipheriv("aes-256-gcm", key(), Buffer.from(ivRaw, "base64url"));
    decipher.setAuthTag(Buffer.from(tagRaw, "base64url"));
    const plaintext = Buffer.concat([
      decipher.update(Buffer.from(bodyRaw, "base64url")),
      decipher.final()
    ]);
    return JSON.parse(plaintext.toString("utf8")) as T;
  } catch {
    return null;
  }
}
