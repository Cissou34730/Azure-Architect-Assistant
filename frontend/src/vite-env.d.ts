/// <reference types="vite/client" />

interface ImportMetaEnv {
  // eslint-disable-next-line @typescript-eslint/naming-convention
  readonly VITE_API_BASE: string;
  // eslint-disable-next-line @typescript-eslint/naming-convention
  readonly VITE_BANNER_MESSAGE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
