"use client";

import Cookies from "js-cookie";
import { authApi, type User } from "./api";

const TOKEN_KEY = "access_token";
const USER_KEY = "sih_user";

export function saveAuth(token: string, user: User) {
  Cookies.set(TOKEN_KEY, token, { expires: 1, sameSite: "strict" });
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  Cookies.remove(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  return !!Cookies.get(TOKEN_KEY);
}
