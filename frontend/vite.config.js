import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
export default defineConfig({
 plugins:[react()],
 test:{environment:'jsdom',include:['tests/ui/**/*.test.jsx'],testTimeout:20000},
 server:{proxy:{'/api':'http://127.0.0.1:8000','/health':'http://127.0.0.1:8000','/ready':'http://127.0.0.1:8000'}},
})
