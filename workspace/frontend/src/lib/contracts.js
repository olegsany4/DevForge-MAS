export async function loadContracts() {
    // Контракты могут отдаваться бекендом по /CONTRACTS.json или лежать в /public
    const res = await fetch('/CONTRACTS.json', { cache: 'no-store' });
    if (!res.ok)
        throw new Error(`HTTP ${res.status}`);
    return res.json();
}
export function groupEndpoints(c) {
    const map = new Map();
    for (const ep of c.endpoints || []) {
        const tag = ep.tag || 'general';
        if (!map.has(tag))
            map.set(tag, []);
        map.get(tag).push(ep);
    }
    return Array.from(map.entries()).map(([tag, items]) => ({
        tag,
        items: items.sort((a, b) => a.path.localeCompare(b.path))
    }));
}
