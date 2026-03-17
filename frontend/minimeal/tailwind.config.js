/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{js,jsx,ts,tsx}', './components/**/*.{js,jsx,ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        canvas: '#f7f6f3',
        ink: '#161616',
        muted: '#7d7d7d',
        line: '#ddd9d3',
        card: '#fffdfa',
        accent: '#8fb7b1',
        accentSoft: '#e8f0ee',
        warm: '#f3e6d9',
      },
      borderRadius: {
        card: '28px',
      },
      boxShadow: {
        float: '0px 10px 30px rgba(28, 28, 28, 0.08)',
      },
      fontFamily: {
        sans: ['System'],
      },
    },
  },
  plugins: [],
};
