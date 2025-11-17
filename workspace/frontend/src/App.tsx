// workspace/frontend/src/App.tsx
import React, { useEffect, useMemo, useState } from 'react';
import { loadContracts, type ApiContract, groupEndpoints } from './lib/contracts';
import EndpointCard from './components/EndpointCard';

export default function App() {
  const [contracts, setContracts] = useState<ApiContract | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadContracts()
      .then(setContracts)
      .catch((e) => setError(String(e)));
  }, []);

  const grouped = useMemo(() => (contracts ? groupEndpoints(contracts) : []), [contracts]);

  return (
    <div className="container">
      <header className="header">
        <h1>DevForge-MAS • API Console</h1>
        <p className="muted">
          Минимальный UI по CONTRACTS.json. Выберите эндпоинт, заполните форму (если есть схема) и выполните запрос.
        </p>
      </header>

      {error && <div className="error">Ошибка загрузки контрактов: {error}</div>}
      {!contracts && !error && <div className="skeleton">Загрузка CONTRACTS.json…</div>}

      {grouped.map((group) => (
        <section key={group.tag} className="group">
          <h2>{group.tag}</h2>
          <div className="grid">
            {group.items.map((ep) => (
              <EndpointCard key={`${ep.method} ${ep.path}`} endpoint={ep} />
            ))}
          </div>
        </section>
      ))}

      {contracts && grouped.length === 0 && (
        <div className="muted">Контракты загружены, но эндпоинтов не найдено.</div>
      )}

      <footer className="footer">
        <small>Источник контрактов: <code>/CONTRACTS.json</code>. Proxy API: <code>/api</code> → <code>localhost:8000</code>.</small>
      </footer>
    </div>
  );
}
