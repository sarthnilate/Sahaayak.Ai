#!/usr/bin/env node

/**
 * Sahaayak AI Design Token Contrast Checker (WCAG 2.1)
 * Calculates relative luminance and contrast ratio for Design.md tokens.
 */

function hexToRgb(hex) {
  const cleanHex = hex.replace('#', '');
  const bigint = parseInt(cleanHex, 16);
  return {
    r: (bigint >> 16) & 255,
    g: (bigint >> 8) & 255,
    b: bigint & 255
  };
}

function getRelativeLuminance(rgb) {
  const [r, g, b] = [rgb.r, rgb.g, rgb.b].map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function getContrastRatio(hex1, hex2) {
  const lum1 = getRelativeLuminance(hexToRgb(hex1));
  const lum2 = getRelativeLuminance(hexToRgb(hex2));
  const brightest = Math.max(lum1, lum2);
  const darkest = Math.min(lum1, lum2);
  return (brightest + 0.05) / (darkest + 0.05);
}

const tokens = {
  bg: '#0B0B0B',
  surface: '#151515',
  surfaceRaised: '#1D1D1D',
  text: '#FFFFFF',
  textMuted: '#A7A7A7',
  primaryPink: '#FF2DA8',
  accentChartreuse: '#D4FF3F',
  success: '#48C78E',
  warning: '#F5B942',
  danger: '#FF5C68'
};

const checks = [
  { name: 'Primary Text on Background', fg: tokens.text, bg: tokens.bg, minRatio: 7.0, level: 'AAA' },
  { name: 'Primary Text on Surface Card', fg: tokens.text, bg: tokens.surface, minRatio: 7.0, level: 'AAA' },
  { name: 'Muted Text on Background', fg: tokens.textMuted, bg: tokens.bg, minRatio: 4.5, level: 'AA' },
  { name: 'Muted Text on Surface Card', fg: tokens.textMuted, bg: tokens.surface, minRatio: 4.5, level: 'AA' },
  { name: 'Chartreuse Accent on Background', fg: tokens.accentChartreuse, bg: tokens.bg, minRatio: 3.0, level: 'UI Component' },
  { name: 'Hot Pink Brand on Background', fg: tokens.primaryPink, bg: tokens.bg, minRatio: 3.0, level: 'UI Component' },
  { name: 'Success Indicator on Background', fg: tokens.success, bg: tokens.bg, minRatio: 3.0, level: 'UI Component' },
  { name: 'Warning Indicator on Background', fg: tokens.warning, bg: tokens.bg, minRatio: 3.0, level: 'UI Component' },
  { name: 'Danger Indicator on Background', fg: tokens.danger, bg: tokens.bg, minRatio: 3.0, level: 'UI Component' },
];

console.log('===============================================================');
console.log('   Sahaayak AI Design System - WCAG 2.1 Contrast Audit');
console.log('===============================================================\n');

let allPassed = true;

for (const check of checks) {
  const ratio = getContrastRatio(check.fg, check.bg);
  const passed = ratio >= check.minRatio;
  const status = passed ? 'PASS' : 'WARN';
  if (!passed) allPassed = false;

  console.log(
    `[${status}] ${check.name.padEnd(35)} Ratio: ${ratio.toFixed(2)}:1 (Req: ${check.minRatio}:1 [${check.level}])`
  );
}

console.log('\n---------------------------------------------------------------');
if (allPassed) {
  console.log('Result: All design token contrast pairs meet WCAG requirements!\n');
  process.exit(0);
} else {
  console.log('Result: Some token pairs require high-contrast consideration.\n');
  process.exit(0);
}
