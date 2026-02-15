import { useEffect, useMemo, useState } from "react";

export type ThemePreference = "light" | "dark" | "system";

const THEME_STORAGE_KEY = "aaa-theme-preference";

function getSystemTheme(): Exclude<ThemePreference, "system"> {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function getSavedPreference(): ThemePreference {
  const savedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (savedTheme === "light" || savedTheme === "dark" || savedTheme === "system") {
    return savedTheme;
  }
  return "system";
}

function applyTheme(preference: ThemePreference): Exclude<ThemePreference, "system"> {
  const resolvedTheme = preference === "system" ? getSystemTheme() : preference;
  document.documentElement.setAttribute("data-theme", resolvedTheme);
  return resolvedTheme;
}

export function initializeTheme() {
  applyTheme(getSavedPreference());
}

export function useTheme() {
  const [preference, setPreferenceState] = useState<ThemePreference>(() => getSavedPreference());
  const [resolvedTheme, setResolvedTheme] = useState<Exclude<ThemePreference, "system">>(() =>
    applyTheme(getSavedPreference()),
  );

  useEffect(() => {
    const nextTheme = applyTheme(preference);
    setResolvedTheme(nextTheme);

    if (preference !== "system") {
      return;
    }

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleSystemChange = () => {
      setResolvedTheme(applyTheme("system"));
    };

    mediaQuery.addEventListener("change", handleSystemChange);
    return () => {
      mediaQuery.removeEventListener("change", handleSystemChange);
    };
  }, [preference]);

  const setPreference = (nextPreference: ThemePreference) => {
    window.localStorage.setItem(THEME_STORAGE_KEY, nextPreference);
    setPreferenceState(nextPreference);
  };

  return useMemo(
    () => ({
      preference,
      resolvedTheme,
      setPreference,
    }),
    [preference, resolvedTheme],
  );
}
