import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
var fromRoot = function (target) { return path.resolve(path.dirname(fileURLToPath(import.meta.url)), target); };
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            app: fromRoot("src/app"),
            pages: fromRoot("src/pages"),
            widgets: fromRoot("src/widgets"),
            features: fromRoot("src/features"),
            entities: fromRoot("src/entities"),
            shared: fromRoot("src/shared")
        }
    },
    server: {
        port: 4173
    }
});
