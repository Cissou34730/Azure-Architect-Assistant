export function getStatusVariant(
  status: string,
): "success" | "warning" | "default" | "error" {
  const s = status.toLowerCase();
  if (s === "accepted") return "success";
  if (s === "draft") return "warning";
  if (s === "deprecated" || s === "superseded") return "error";
  return "default";
}
