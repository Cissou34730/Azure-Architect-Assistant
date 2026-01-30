/**
 * API Configuration
 */

const envBackendVal = import.meta.env.BACKEND_URL;
const envBackendUrl = typeof envBackendVal === "string" ? envBackendVal : "";
const BACKEND_URL =
  envBackendUrl !== "" ? envBackendUrl : "http://localhost:8000";
export const API_BASE = `${BACKEND_URL}/api`;
