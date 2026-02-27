import sharp from "sharp";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const svgPath = resolve(__dirname, "../src/app/icon.svg");

const targets = [
  { size: 192, output: resolve(__dirname, "../public/icon-192.png") },
  { size: 512, output: resolve(__dirname, "../public/icon-512.png") },
  { size: 180, output: resolve(__dirname, "../src/app/apple-icon.png") },
];

for (const { size, output } of targets) {
  await sharp(svgPath).resize(size, size).png().toFile(output);
  console.log(`Generated: ${output} (${size}x${size})`);
}
