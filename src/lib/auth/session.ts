import { getIronSession, type SessionOptions } from "iron-session";
import { cookies } from "next/headers";
import { config } from "@/lib/config";

export type SessionData = {
  userId?: number;
  csrfToken?: string;
  isLoggedIn: boolean;
};

export const sessionOptions: SessionOptions = {
  password: config.sessionSecret.padEnd(32, "!").slice(0, 64),
  cookieName: "printdrop_session",
  cookieOptions: {
    httpOnly: true,
    secure: config.secureCookies,
    sameSite: config.cookieSameSite,
    maxAge: config.sessionMaxAgeSeconds,
    path: "/",
  },
};

export async function getSession() {
  return getIronSession<SessionData>(await cookies(), sessionOptions);
}

export function newCsrfToken(): string {
  return crypto.randomUUID().replace(/-/g, "") + crypto.randomUUID().replace(/-/g, "");
}
