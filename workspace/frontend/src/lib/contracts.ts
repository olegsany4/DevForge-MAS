// workspace/frontend/src/lib/contracts.ts
export type Endpoint = {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  path: string;
  tag: string;
  summary?: string;
  querySchema?: any;
  pathParams?: string[]; // e.g. ["id"]
  requestBodySchema?: any;
  responseSchema?: any;
};

export type ApiContract = {
  endpoints: Endpoint[];
  schemas?: Record<string, any>;
};

export async function loadContracts(): Promise<ApiContract> {
  // Контракты могут отдаваться бекендом по /CONTRACTS.json или лежать в /public
  const res = await fetch('/CONTRACTS.json', { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export function groupEndpoints(c: ApiContract): { tag: string; items: Endpoint[] }[] {
  const map = new Map<string, Endpoint[]>();
  for (const ep of c.endpoints || []) {
    const tag = ep.tag || 'general';
    if (!map.has(tag)) map.set(tag, []);
    map.get(tag)!.push(ep);
  }
  return Array.from(map.entries()).map(([tag, items]) => ({
    tag,
    items: items.sort((a, b) => a.path.localeCompare(b.path))
  }));
}
