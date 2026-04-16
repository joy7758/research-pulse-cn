import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

const coreEntryPath = fileURLToPath(
  new URL("../../packages/subscription-editor-core/src/index.ts", import.meta.url),
);
const repoRootPath = fileURLToPath(new URL("../..", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@research-pulse/subscription-editor-core": coreEntryPath,
    },
  },
  server: {
    fs: {
      allow: [repoRootPath],
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
