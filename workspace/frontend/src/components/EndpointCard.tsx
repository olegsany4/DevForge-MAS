// workspace/frontend/src/components/EndpointCard.tsx
import React, { useMemo, useState } from 'react';
import { buildUrl, callApi, type Endpoint, extractSchemaProps } from '../lib/api';
import SchemaForm from './SchemaForm';

type View = 'request' | 'response';

export default function EndpointCard({ endpoint }: { endpoint: Endpoint }) {
  const [view, setView] = useState<View>('request');
  const [resp, setResp] = useState<{ ok: boolean; status: number; body: unknown } | null>(null);
  const [loading, setLoading] = useState(false);
  const [pathParams, setPathParams] = useState<Record<string, string>>({});
  const [queryParams, setQueryParams] = useState<Record<string, string>>({});
  const [body, setBody] = useState<any>({});
  const [error, setError] = useState<string | null>(null);

  const { pathParamNames, hasQuery, hasBody, bodySchema } = useMemo(
    () => extractSchemaProps(endpoint),
    [endpoint]
  );

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    setResp(null);
    try {
      const url = buildUrl(endpoint.path, pathParams, queryParams);
      const r = await callApi(endpoint.method, url, hasBody ? body : undefined);
      setResp(r);
      setView('response');
    } catch (e: any) {
      setError(String(e));
      setView('response');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="card-head">
        <span className={`method method-${endpoint.method.toLowerCase()}`}>{endpoint.method}</span>
        <code className="path">{endpoint.path}</code>
      </div>
      <div className="card-sub">
        <span className="tag">{endpoint.tag}</span>
        {endpoint.summary && <span className="summary">{endpoint.summary}</span>}
      </div>

      <div className="tabs">
        <button className={view === 'request' ? 'tab active' : 'tab'} onClick={() => setView('request')}>
          Request
        </button>
        <button className={view === 'response' ? 'tab active' : 'tab'} onClick={() => setView('response')}>
          Response
        </button>
      </div>

      {view === 'request' && (
        <div className="stack">
          {pathParamNames.length > 0 && (
            <div className="block">
              <h4>Path params</h4>
              {pathParamNames.map((p) => (
                <label key={p} className="row">
                  <span className="lbl">{p}</span>
                  <input
                    className="txt"
                    placeholder={`:${p}`}
                    value={pathParams[p] || ''}
                    onChange={(e) => setPathParams({ ...pathParams, [p]: e.target.value })}
                  />
                </label>
              ))}
            </div>
          )}

          {hasQuery && (
            <div className="block">
              <h4>Query params</h4>
              <ParamEditor value={queryParams} onChange={setQueryParams} />
            </div>
          )}

          {hasBody && (
            <div className="block">
              <h4>Body</h4>
              <SchemaForm schema={bodySchema} value={body} onChange={setBody} />
            </div>
          )}

          <div className="actions">
            <button className="btn" onClick={handleSubmit} disabled={loading}>
              {loading ? 'Выполняю…' : 'Send'}
            </button>
            {error && <span className="error-inline">{error}</span>}
          </div>
        </div>
      )}

      {view === 'response' && (
        <pre className="pre">
          {resp ? JSON.stringify(resp, null, 2) : error ? error : 'Ответа ещё нет.'}
        </pre>
      )}
    </div>
  );
}

function ParamEditor({
  value,
  onChange
}: {
  value: Record<string, string>;
  onChange: (v: Record<string, string>) => void;
}) {
  const [k, setK] = useState('');
  const [v, setV] = useState('');
  const pairs = Object.entries(value);

  return (
    <div className="param-editor">
      <div className="row">
        <input className="txt" placeholder="key" value={k} onChange={(e) => setK(e.target.value)} />
        <input className="txt" placeholder="value" value={v} onChange={(e) => setV(e.target.value)} />
        <button
          className="btn secondary"
          onClick={() => {
            if (!k) return;
            onChange({ ...value, [k]: v });
            setK('');
            setV('');
          }}
        >
          Add
        </button>
      </div>
      {pairs.length > 0 && (
        <ul className="kv">
          {pairs.map(([kk, vv]) => (
            <li key={kk}>
              <code>{kk}</code>=<code>{vv}</code>
              <button
                className="icon-btn"
                title="remove"
                onClick={() => {
                  const n = { ...value };
                  delete n[kk];
                  onChange(n);
                }}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
