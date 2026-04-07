/**
 * API Configuration
 */

const envApiBaseVal = import.meta.env.VITE_API_BASE;
const envApiBase = typeof envApiBaseVal === "string" ? envApiBaseVal.trim() : "";

if (envApiBase === "") {
  throw new Error("VITE_API_BASE is required in .env");
}

export const API_BASE = envApiBase;
