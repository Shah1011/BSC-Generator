module.exports = {
  content: [
    './bsc_gen/templates/**/*.html',
    './bsc_gen/**/*.py',
  ],
  safelist: [
    'bg-green-500', 'bg-yellow-400', 'bg-red-500',
    'border-green-700', 'border-yellow-600', 'border-red-700'
  ],
  theme: {
    extend: {},
  },
  plugins: [],
  mode: 'jit',
}