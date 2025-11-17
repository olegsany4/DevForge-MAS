import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// workspace/frontend/src/App.tsx
import { useEffect, useMemo, useState } from 'react';
import { loadContracts, groupEndpoints } from './lib/contracts';
import EndpointCard from './components/EndpointCard';
export default function App() {
    const [contracts, setContracts] = useState(null);
    const [error, setError] = useState(null);
    useEffect(() => {
        loadContracts()
            .then(setContracts)
            .catch((e) => setError(String(e)));
    }, []);
    const grouped = useMemo(() => (contracts ? groupEndpoints(contracts) : []), [contracts]);
    return (_jsxs("div", { className: "container", children: [_jsxs("header", { className: "header", children: [_jsx("h1", { children: "DevForge-MAS \u2022 API Console" }), _jsx("p", { className: "muted", children: "\u041C\u0438\u043D\u0438\u043C\u0430\u043B\u044C\u043D\u044B\u0439 UI \u043F\u043E CONTRACTS.json. \u0412\u044B\u0431\u0435\u0440\u0438\u0442\u0435 \u044D\u043D\u0434\u043F\u043E\u0438\u043D\u0442, \u0437\u0430\u043F\u043E\u043B\u043D\u0438\u0442\u0435 \u0444\u043E\u0440\u043C\u0443 (\u0435\u0441\u043B\u0438 \u0435\u0441\u0442\u044C \u0441\u0445\u0435\u043C\u0430) \u0438 \u0432\u044B\u043F\u043E\u043B\u043D\u0438\u0442\u0435 \u0437\u0430\u043F\u0440\u043E\u0441." })] }), error && _jsxs("div", { className: "error", children: ["\u041E\u0448\u0438\u0431\u043A\u0430 \u0437\u0430\u0433\u0440\u0443\u0437\u043A\u0438 \u043A\u043E\u043D\u0442\u0440\u0430\u043A\u0442\u043E\u0432: ", error] }), !contracts && !error && _jsx("div", { className: "skeleton", children: "\u0417\u0430\u0433\u0440\u0443\u0437\u043A\u0430 CONTRACTS.json\u2026" }), grouped.map((group) => (_jsxs("section", { className: "group", children: [_jsx("h2", { children: group.tag }), _jsx("div", { className: "grid", children: group.items.map((ep) => (_jsx(EndpointCard, { endpoint: ep }, `${ep.method} ${ep.path}`))) })] }, group.tag))), contracts && grouped.length === 0 && (_jsx("div", { className: "muted", children: "\u041A\u043E\u043D\u0442\u0440\u0430\u043A\u0442\u044B \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043D\u044B, \u043D\u043E \u044D\u043D\u0434\u043F\u043E\u0438\u043D\u0442\u043E\u0432 \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u043E." })), _jsx("footer", { className: "footer", children: _jsxs("small", { children: ["\u0418\u0441\u0442\u043E\u0447\u043D\u0438\u043A \u043A\u043E\u043D\u0442\u0440\u0430\u043A\u0442\u043E\u0432: ", _jsx("code", { children: "/CONTRACTS.json" }), ". Proxy API: ", _jsx("code", { children: "/api" }), " \u2192 ", _jsx("code", { children: "localhost:8000" }), "."] }) })] }));
}
