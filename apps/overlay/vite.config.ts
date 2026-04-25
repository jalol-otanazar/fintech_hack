import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  base: './',
  build: { outDir: 'build' },
  resolve: {
    alias: [
      {
        find: /.*shared\/types\/models/,
        replacement: path.resolve(__dirname, '../../shared/types/models'),
      },
    ],
  },
})
