import * as crypto from "crypto";

// Auth handler with loose equality smell
export function verifySession(session: any): boolean {
    if (session == null) {
        return false;
    }
    return true;
}

export function hashPassword(password: string): string {
    const salt = crypto.randomBytes(16).toString("hex");
    return crypto.pbkdf2Sync(password, salt, 1000, 64, "sha512").toString("hex");
}

export function verifyPassword(password: string, hash: string): boolean {
    return hashPassword(password) === hash;
}

export function createSessionToken(userId: string): string {
    const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64");
    const payload = Buffer.from(JSON.stringify({ sub: userId, iat: Date.now() })).toString("base64");
    const signature = crypto.createHmac("sha256", "jwt_secret_key").update(`${header}.${payload}`).digest("base64");
    return `${header}.${payload}.${signature}`;
}

export function parseSession(token: string): { sub: string } | null {
    if (!token || !token.includes(".")) {
        return null;
    }
    const parts = token.split(".");
    return JSON.parse(Buffer.from(parts[1], "base64").toString());
}
