import sharp from "sharp";
import { writeFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));

const appEnv = process.env.NEXT_PUBLIC_APP_ENV || "prod";
const bgColor = appEnv === "dev" ? "#EAB308" : "#2563EB";

console.log(`Generating icons for env=${appEnv}, bgColor=${bgColor}`);

const iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <rect width="24" height="24" rx="5" fill="${bgColor}"/>
  <path fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"
    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
</svg>`;

const iconSvgPath = resolve(__dirname, "../src/app/icon.svg");
writeFileSync(iconSvgPath, iconSvg, "utf8");
console.log(`Generated: ${iconSvgPath} (SVG)`);

const badgeSvgPath = resolve(__dirname, "../src/app/icon-badge.svg");

const targets = [
  { svg: iconSvgPath, size: 192, output: resolve(__dirname, "../public/icon-192.png") },
  { svg: iconSvgPath, size: 512, output: resolve(__dirname, "../public/icon-512.png") },
  { svg: iconSvgPath, size: 180, output: resolve(__dirname, "../src/app/apple-icon.png") },
  { svg: badgeSvgPath, size: 72, output: resolve(__dirname, "../public/icon-badge-72.png") },
];

for (const { svg, size, output } of targets) {
  await sharp(svg).resize(size, size).png().toFile(output);
  console.log(`Generated: ${output} (${size}x${size})`);
}
