// workspace/frontend/src/lib/api.ts
export type Endpoint = import('./contracts').Endpoint;

export function extractSchemaProps(endpoint: Endpoint) {
  const pathParamNames = endpoint.pathParams || findPathParams(endpoint.path);
  const hasQuery = !!endpoint.querySchema;
  const hasBody = !!endpoint.requestBodySchema;
  const bodySchema = endpoint.requestBodySchema;
  return { pathParamNames, hasQuery, hasBody, bodySchema };
}

export function buildUrl(
  pathTemplate: string,
  pathParams: Record<string, string>,
  query: Record<string, string>
) {
  let path = pathTemplate;
  for (const [k, v] of Object.entries(pathParams || {})) {
    path = path.replace(new RegExp(`:${k}\\b`, 'g'), encodeURIComponent(v));
    path = path.replace(new RegExp(`\\{${k}\\}`, 'g'), encodeURIComponent(v));
  }
  const q = new URLSearchParams(query || {});
  const qs = q.toString();
  const base = path.startsWith('/api') ? path : `/api${path.startsWith('/') ? '' : '/'}${path}`;
  return qs ? `${base}?${qs}` : base;
}

export async function callApi(
  method: string,
  url: string,
  body?: unknown
): Promise<{ ok: boolean; status: number; body: unknown }> {
  const init: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' }
  };
  if (body !== undefined) init.body = JSON.stringify(body);
  const res = await fetch(url, init);
  let payload: unknown = null;
  const text = await res.text();
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = text;
  }
  return { ok: res.ok, status: res.status, body: payload };
}

function findPathParams(path: string): string[] {
  const names = new Set<string>();
  const colon = path.match(/:([a-zA-Z0-9_]+)/g) || [];
  colon.forEach((m) => names.add(m.slice(1)));
  const braces = path.match(/\{([a-zA-Z0-9_]+)\}/g) || [];
  braces.forEach((m) => names.add(m.slice(1, -1)));
  return Array.from(names);
}
