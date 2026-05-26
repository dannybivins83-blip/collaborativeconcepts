const fs = require('fs');
const { Resvg } = require('@resvg/resvg-js');

// Redlight mark: an attention ring (signal orange) with a gap at the bottom-right,
// echoing the in-app AttentionRing, over the dark radial background. A single
// orange dot sits in the gap — the "go" signal.

function iconSvg(size, { bleed = false } = {}) {
  const cx = size / 2;
  const cy = size / 2;
  // Adaptive icons get cropped to a circle/squircle, so keep the mark well inside.
  const safe = bleed ? 0.62 : 0.72;
  const r = (size / 2) * safe;
  const stroke = size * 0.07;
  const c = 2 * Math.PI * r;
  const gap = c * 0.22; // 22% gap
  const dash = c - gap;
  const dotR = size * 0.062;
  // place the dot near the end of the arc gap (bottom-right)
  const dotAngle = (-90 + 360 * (1 - 0.11)) * (Math.PI / 180);
  const dotX = cx + r * Math.cos(dotAngle);
  const dotY = cy + r * Math.sin(dotAngle);

  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="bg" cx="50%" cy="32%" r="85%">
      <stop offset="0%" stop-color="#1a1410"/>
      <stop offset="55%" stop-color="#0a0807"/>
      <stop offset="100%" stop-color="#000000"/>
    </radialGradient>
  </defs>
  <rect x="0" y="0" width="${size}" height="${size}" fill="url(#bg)"/>
  <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="rgba(245,233,212,0.08)" stroke-width="${stroke}"/>
  <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#ff6b35" stroke-width="${stroke}"
    stroke-linecap="round" stroke-dasharray="${dash} ${c}"
    transform="rotate(-90 ${cx} ${cy})"/>
  <circle cx="${dotX}" cy="${dotY}" r="${dotR}" fill="#6dffa6"/>
</svg>`;
}

function splashSvg(w, h) {
  const cx = w / 2;
  const cy = h / 2;
  const r = Math.min(w, h) * 0.13;
  const stroke = r * 0.16;
  const c = 2 * Math.PI * r;
  const gap = c * 0.22;
  const dash = c - gap;
  const dotR = r * 0.18;
  const dotAngle = (-90 + 360 * (1 - 0.11)) * (Math.PI / 180);
  const dotX = cx + r * Math.cos(dotAngle);
  const dotY = cy + r * Math.sin(dotAngle);
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="bg" cx="50%" cy="22%" r="100%">
      <stop offset="0%" stop-color="#1a1410"/>
      <stop offset="50%" stop-color="#0a0807"/>
      <stop offset="100%" stop-color="#000000"/>
    </radialGradient>
  </defs>
  <rect x="0" y="0" width="${w}" height="${h}" fill="url(#bg)"/>
  <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="rgba(245,233,212,0.08)" stroke-width="${stroke}"/>
  <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#ff6b35" stroke-width="${stroke}"
    stroke-linecap="round" stroke-dasharray="${dash} ${c}"
    transform="rotate(-90 ${cx} ${cy})"/>
  <circle cx="${dotX}" cy="${dotY}" r="${dotR}" fill="#6dffa6"/>
  <text x="${cx}" y="${cy + r + Math.min(w, h) * 0.11}" text-anchor="middle"
    font-family="Georgia, 'Times New Roman', serif" font-style="italic"
    font-size="${Math.min(w, h) * 0.058}" fill="#f5e9d4">redlight</text>
</svg>`;
}

function render(svg, outPath, width) {
  const resvg = new Resvg(svg, { fitTo: { mode: 'width', value: width } });
  const png = resvg.render().asPng();
  fs.writeFileSync(outPath, png);
  console.log(`wrote ${outPath} (${width}px, ${png.length} bytes)`);
}

// App icon — 1024 master (App Store requires 1024).
render(iconSvg(1024), 'assets/icon.png', 1024);
// Android adaptive foreground — needs generous safe zone (cropped to squircle/circle).
render(iconSvg(1024, { bleed: true }), 'assets/adaptive-icon.png', 1024);
// Favicon for web.
render(iconSvg(64), 'assets/favicon.png', 64);
// Notification icon (Android tints this; keep it simple but real).
render(iconSvg(96, { bleed: true }), 'assets/notification-icon.png', 96);
// Splash — portrait 1284x2778 (iPhone 14 Pro Max class), cover-fit.
render(splashSvg(1284, 2778), 'assets/splash.png', 1284);
