# Frontend local

Interface React/Vite do E-Scrapper. O servidor de desenvolvimento fica restrito a `127.0.0.1:5173` e encaminha as chamadas da API para `127.0.0.1:8500`.

```powershell
npm install
npm run dev
```

Não configure `VITE_API_URL`: em modo local, as chamadas relativas passam pelo proxy do Vite.
