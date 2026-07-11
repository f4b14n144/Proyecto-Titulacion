/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ups: {
          blue: '#003DA5',
          red: '#E30613',
        },
      },
      // Escala tipográfica un punto por encima de la de Tailwind.
      // El sistema se usa en monitores de baja resolución (1366x768 y menores) y
      // con el tamaño por defecto (xs=12px, sm=14px) el texto queda pequeño.
      // Subirla aquí levanta toda la interfaz sin tocar componente por componente.
      fontSize: {
        xs: ['0.8125rem', { lineHeight: '1.125rem' }],   // 13px (Tailwind: 12)
        sm: ['0.9375rem', { lineHeight: '1.375rem' }],   // 15px (Tailwind: 14)
        base: ['1.0625rem', { lineHeight: '1.625rem' }], // 17px (Tailwind: 16)
        lg: ['1.1875rem', { lineHeight: '1.75rem' }],    // 19px (Tailwind: 18)
        xl: ['1.3125rem', { lineHeight: '1.875rem' }],   // 21px (Tailwind: 20)
        '2xl': ['1.625rem', { lineHeight: '2.125rem' }], // 26px (Tailwind: 24)
      },
    },
  },
  plugins: [],
}
