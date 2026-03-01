import sharp from "sharp";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const svgPath = resolve(__dirname, "../src/app/icon.svg");
const badgeSvgPath = resolve(__dirname, "../src/app/icon-badge.svg");

const targets = [
  { svg: svgPath, size: 192, output: resolve(__dirname, "../public/icon-192.png") },
  { svg: svgPath, size: 512, output: resolve(__dirname, "../public/icon-512.png") },
  { svg: svgPath, size: 180, output: resolve(__dirname, "../src/app/apple-icon.png") },
  { svg: badgeSvgPath, size: 72, output: resolve(__dirname, "../public/icon-badge-72.png") },
];

for (const { svg, size, output } of targets) {
  await sharp(svg).resize(size, size).png().toFile(output);
  console.log(`Generated: ${output} (${size}x${size})`);
}
