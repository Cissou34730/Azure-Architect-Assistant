import React from "react";

interface StateSectionProps {
  readonly icon: string;
  readonly title: string;
  readonly children: React.ReactNode;
}

export function StateSection({ icon, title, children }: StateSectionProps) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-foreground mb-2 flex items-center">
        <span className="mr-2">{icon}</span> {title}
      </h3>
      <div className="bg-surface rounded-lg p-3 space-y-2 text-sm">
        {children}
      </div>
    </div>
  );
}

interface StateFieldProps {
  readonly label: string;
  readonly children: React.ReactNode;
}

export function StateField({ label, children }: StateFieldProps) {
  return (
    <div>
      <span className="font-medium text-secondary">{label}:</span>
      {children}
    </div>
  );
}

