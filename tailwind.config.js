/** WWS public-site Tailwind build (replaces the runtime CDN on public pages).
 *  Admin/portal/send/design tools stay on the CDN (they build class names in JS).
 *  Rebuild after editing public HTML:  npm run build:css
 */
module.exports = {
  darkMode: 'class',
  // NOTE: Tailwind v3 does NOT support "!" negation in content globs — using
  // them silently degrades the scan and drops variant (sm:/md:/lg:/hover:)
  // generation. List the public page locations explicitly instead.
  content: [
    './wwslgc/*.html',
    './wwslgc/guides/*.html',
  ],
  safelist: ['hidden'],
  theme: {
    extend: {
      colors: {
        primary: '#13233f', 'primary-container': '#1e3a5f',
        secondary: '#c9a227', 'secondary-container': '#e8c547',
        'secondary-fixed': '#f0d060', 'on-secondary-fixed': '#3d2e00',
        steel: '#8b97a8', surface: '#f7f6f3',
        'surface-container-low': '#f0eee8', 'surface-container-lowest': '#ffffff',
        'surface-container-high': '#e8e5dd', 'on-surface': '#1a1a1a',
        'on-surface-variant': '#54606f', 'outline-variant': '#dcd8cf',
        'on-primary': '#ffffff',
      },
      borderRadius: { DEFAULT: '0.625rem', lg: '0.875rem', xl: '1.25rem', '2xl': '1.5rem', full: '9999px' },
      fontFamily: { headline: ['Manrope'], body: ['Inter'], label: ['Inter'] },
    },
  },
  plugins: [require('@tailwindcss/forms'), require('@tailwindcss/container-queries')],
};
