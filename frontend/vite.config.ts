import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server on port 3000; talks to the API via VITE_API_URL.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
  },
});
