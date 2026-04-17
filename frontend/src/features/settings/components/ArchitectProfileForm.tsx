import { useEffect, useMemo, useState } from "react";
import {
  settingsApi,
  type ArchitectProfile,
} from "../api/settingsService";

const DEFAULT_PROFILE: ArchitectProfile = {
  defaultRegionPrimary: "eastus",
  defaultRegionSecondary: null,
  defaultIacFlavor: "bicep",
  complianceBaseline: [],
  monthlyCostCeiling: null,
  preferredVmSeries: [],
  teamDevopsMaturity: "basic",
  notes: "",
};

function toCsv(values: readonly string[]): string {
  return values.join(", ");
}

function parseCsv(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

export function ArchitectProfileForm({
  onClose,
}: {
  readonly onClose: () => void;
}) {
  const [profile, setProfile] = useState<ArchitectProfile>(DEFAULT_PROFILE);
  const [complianceBaseline, setComplianceBaseline] = useState("");
  const [preferredVmSeries, setPreferredVmSeries] = useState("");
  const [monthlyCostCeiling, setMonthlyCostCeiling] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const loadProfile = async () => {
      setLoading(true);
      try {
        const response = await settingsApi.fetchArchitectProfile();
        if (!active) {
          return;
        }
        setProfile(response.profile);
        setComplianceBaseline(toCsv(response.profile.complianceBaseline));
        setPreferredVmSeries(toCsv(response.profile.preferredVmSeries));
        setMonthlyCostCeiling(
          response.profile.monthlyCostCeiling === null
            ? ""
            : String(response.profile.monthlyCostCeiling),
        );
        setError(null);
      } catch (loadError) {
        if (!active) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Failed to load architect profile.");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void loadProfile();
    return () => {
      active = false;
    };
  }, []);

  const canSave = useMemo(
    () => !loading && !saving && profile.defaultRegionPrimary.trim().length > 0,
    [loading, profile.defaultRegionPrimary, saving],
  );

  const handleSave = async () => {
    setSaving(true);
    setStatusMessage(null);
    setError(null);

    try {
      const nextProfile: ArchitectProfile = {
        ...profile,
        defaultRegionPrimary: profile.defaultRegionPrimary.trim(),
        defaultRegionSecondary:
          profile.defaultRegionSecondary?.trim() !== ""
            ? profile.defaultRegionSecondary?.trim() ?? null
            : null,
        complianceBaseline: parseCsv(complianceBaseline),
        monthlyCostCeiling:
          monthlyCostCeiling.trim() === "" ? null : Number(monthlyCostCeiling),
        preferredVmSeries: parseCsv(preferredVmSeries),
        notes: profile.notes.trim(),
      };
      const response = await settingsApi.updateArchitectProfile(nextProfile);
      setProfile(response.profile);
      setComplianceBaseline(toCsv(response.profile.complianceBaseline));
      setPreferredVmSeries(toCsv(response.profile.preferredVmSeries));
      setMonthlyCostCeiling(
        response.profile.monthlyCostCeiling === null
          ? ""
          : String(response.profile.monthlyCostCeiling),
      );
      setStatusMessage("Architect profile saved.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to save architect profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-surface/70 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="architect-profile-title"
    >
      <div className="w-full max-w-2xl rounded-xl border border-border bg-card shadow-xl">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div>
            <h2 id="architect-profile-title" className="text-lg font-semibold text-foreground">
              Architect profile
            </h2>
            <p className="text-sm text-secondary">
              Personalize default regions, compliance posture, and delivery preferences.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-secondary hover:bg-surface"
          >
            Close
          </button>
        </div>

        <div className="grid gap-4 px-6 py-5 md:grid-cols-2">
          <Field
            label="Primary region"
            value={profile.defaultRegionPrimary}
            onChange={(value) => {
              setProfile((current) => ({ ...current, defaultRegionPrimary: value }));
            }}
            disabled={loading || saving}
          />
          <Field
            label="Secondary region"
            value={profile.defaultRegionSecondary ?? ""}
            onChange={(value) => {
              setProfile((current) => ({ ...current, defaultRegionSecondary: value }));
            }}
            disabled={loading || saving}
          />
          <SelectField
            label="IaC flavor"
            value={profile.defaultIacFlavor}
            onChange={(value) => {
              setProfile((current) => ({
                ...current,
                defaultIacFlavor: value as ArchitectProfile["defaultIacFlavor"],
              }));
            }}
            disabled={loading || saving}
            options={[
              { value: "bicep", label: "Bicep" },
              { value: "terraform", label: "Terraform" },
            ]}
          />
          <SelectField
            label="DevOps maturity"
            value={profile.teamDevopsMaturity}
            onChange={(value) => {
              setProfile((current) => ({
                ...current,
                teamDevopsMaturity: value as ArchitectProfile["teamDevopsMaturity"],
              }));
            }}
            disabled={loading || saving}
            options={[
              { value: "none", label: "None" },
              { value: "basic", label: "Basic" },
              { value: "advanced", label: "Advanced" },
            ]}
          />
          <Field
            label="Compliance baseline"
            value={complianceBaseline}
            onChange={setComplianceBaseline}
            disabled={loading || saving}
            helperText="Comma-separated values"
          />
          <Field
            label="Monthly cost ceiling"
            value={monthlyCostCeiling}
            onChange={setMonthlyCostCeiling}
            disabled={loading || saving}
            type="number"
            helperText="Leave blank for no ceiling"
          />
          <Field
            label="Preferred VM series"
            value={preferredVmSeries}
            onChange={setPreferredVmSeries}
            disabled={loading || saving}
            helperText="Comma-separated values"
          />
          <div className="md:col-span-2">
            <TextAreaField
              label="Notes"
              value={profile.notes}
              onChange={(value) => {
                setProfile((current) => ({ ...current, notes: value }));
              }}
              disabled={loading || saving}
            />
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-border px-6 py-4">
          <div className="min-h-5 text-sm">
            {error !== null ? (
              <span className="text-danger">{error}</span>
            ) : statusMessage !== null ? (
              <span className="text-success">{statusMessage}</span>
            ) : loading ? (
              <span className="text-secondary">Loading profile…</span>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => {
              void handleSave();
            }}
            disabled={!canSave}
            className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-inverse hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save profile"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  disabled,
  type = "text",
  helperText,
}: {
  readonly label: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly disabled: boolean;
  readonly type?: "text" | "number";
  readonly helperText?: string;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm text-secondary">
      <span className="font-medium text-foreground">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => {
          onChange(event.target.value);
        }}
        disabled={disabled}
        className="rounded-lg border border-border bg-surface px-3 py-2 text-foreground"
      />
      {helperText !== undefined && <span className="text-xs text-dim">{helperText}</span>}
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
  disabled,
  options,
}: {
  readonly label: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly disabled: boolean;
  readonly options: readonly { value: string; label: string }[];
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm text-secondary">
      <span className="font-medium text-foreground">{label}</span>
      <select
        value={value}
        onChange={(event) => {
          onChange(event.target.value);
        }}
        disabled={disabled}
        className="rounded-lg border border-border bg-surface px-3 py-2 text-foreground"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function TextAreaField({
  label,
  value,
  onChange,
  disabled,
}: {
  readonly label: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly disabled: boolean;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm text-secondary">
      <span className="font-medium text-foreground">{label}</span>
      <textarea
        value={value}
        onChange={(event) => {
          onChange(event.target.value);
        }}
        disabled={disabled}
        rows={5}
        className="rounded-lg border border-border bg-surface px-3 py-2 text-foreground"
      />
    </label>
  );
}
