export const colors = {
  bgStart: '#1a1410',
  bgMid: '#0a0807',
  bgEnd: '#000000',
  text: '#f5e9d4',
  accent: '#ff6b35',
  danger: '#ff2d2d',
  success: '#6dffa6',
  muted: '#88766a',
  border: 'rgba(245, 233, 212, 0.08)',
  borderStrong: 'rgba(245, 233, 212, 0.18)',
  cardBg: 'rgba(245, 233, 212, 0.03)',
  overlayDark: 'rgba(0, 0, 0, 0.6)',
} as const;

export const fonts = {
  serifItalic: 'DMSerifDisplay-Italic',
  serif: 'DMSerifDisplay',
  mono: 'JetBrainsMono',
  monoBold: 'JetBrainsMono-Bold',
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

export const radius = {
  none: 0,
  sm: 2,
  md: 4,
} as const;

export const typography = {
  eyebrow: {
    fontFamily: fonts.mono,
    fontSize: 11,
    letterSpacing: 1.8,
    color: colors.muted,
    textTransform: 'uppercase' as const,
  },
  label: {
    fontFamily: fonts.mono,
    fontSize: 10,
    letterSpacing: 1.5,
    color: colors.muted,
    textTransform: 'uppercase' as const,
  },
  monoBody: {
    fontFamily: fonts.mono,
    fontSize: 13,
    color: colors.text,
  },
  serifHero: {
    fontFamily: fonts.serifItalic,
    fontSize: 56,
    color: colors.text,
    lineHeight: 60,
  },
  serifH1: {
    fontFamily: fonts.serifItalic,
    fontSize: 36,
    color: colors.text,
    lineHeight: 40,
  },
  serifH2: {
    fontFamily: fonts.serifItalic,
    fontSize: 24,
    color: colors.text,
    lineHeight: 28,
  },
  numberBig: {
    fontFamily: fonts.serifItalic,
    fontSize: 88,
    color: colors.text,
    lineHeight: 92,
  },
} as const;

export const gradientBg = [colors.bgStart, colors.bgMid, colors.bgEnd] as const;
