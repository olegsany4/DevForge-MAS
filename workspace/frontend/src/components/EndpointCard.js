import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// workspace/frontend/src/components/EndpointCard.tsx
import { useMemo, useState } from 'react';
import { buildUrl, callApi, extractSchemaProps } from '../lib/api';
import SchemaForm from './SchemaForm';
export default function EndpointCard({ endpoint }) {
    const [view, setView] = useState('request');
    const [resp, setResp] = useState(null);
    const [loading, setLoading] = useState(false);
    const [pathParams, setPathParams] = useState({});
    const [queryParams, setQueryParams] = useState({});
    const [body, setBody] = useState({});
    const [error, setError] = useState(null);
    const { pathParamNames, hasQuery, hasBody, bodySchema } = useMemo(() => extractSchemaProps(endpoint), [endpoint]);
    const handleSubmit = async () => {
        setLoading(true);
        setError(null);
        setResp(null);
        try {
            const url = buildUrl(endpoint.path, pathParams, queryParams);
            const r = await callApi(endpoint.method, url, hasBody ? body : undefined);
            setResp(r);
            setView('response');
        }
        catch (e) {
            setError(String(e));
            setView('response');
        }
        finally {
            setLoading(false);
        }
    };
    return (_jsxs("div", { className: "card", children: [_jsxs("div", { className: "card-head", children: [_jsx("span", { className: `method method-${endpoint.method.toLowerCase()}`, children: endpoint.method }), _jsx("code", { className: "path", children: endpoint.path })] }), _jsxs("div", { className: "card-sub", children: [_jsx("span", { className: "tag", children: endpoint.tag }), endpoint.summary && _jsx("span", { className: "summary", children: endpoint.summary })] }), _jsxs("div", { className: "tabs", children: [_jsx("button", { className: view === 'request' ? 'tab active' : 'tab', onClick: () => setView('request'), children: "Request" }), _jsx("button", { className: view === 'response' ? 'tab active' : 'tab', onClick: () => setView('response'), children: "Response" })] }), view === 'request' && (_jsxs("div", { className: "stack", children: [pathParamNames.length > 0 && (_jsxs("div", { className: "block", children: [_jsx("h4", { children: "Path params" }), pathParamNames.map((p) => (_jsxs("label", { className: "row", children: [_jsx("span", { className: "lbl", children: p }), _jsx("input", { className: "txt", placeholder: `:${p}`, value: pathParams[p] || '', onChange: (e) => setPathParams({ ...pathParams, [p]: e.target.value }) })] }, p)))] })), hasQuery && (_jsxs("div", { className: "block", children: [_jsx("h4", { children: "Query params" }), _jsx(ParamEditor, { value: queryParams, onChange: setQueryParams })] })), hasBody && (_jsxs("div", { className: "block", children: [_jsx("h4", { children: "Body" }), _jsx(SchemaForm, { schema: bodySchema, value: body, onChange: setBody })] })), _jsxs("div", { className: "actions", children: [_jsx("button", { className: "btn", onClick: handleSubmit, disabled: loading, children: loading ? 'Выполняю…' : 'Send' }), error && _jsx("span", { className: "error-inline", children: error })] })] })), view === 'response' && (_jsx("pre", { className: "pre", children: resp ? JSON.stringify(resp, null, 2) : error ? error : 'Ответа ещё нет.' }))] }));
}
function ParamEditor({ value, onChange }) {
    const [k, setK] = useState('');
    const [v, setV] = useState('');
    const pairs = Object.entries(value);
    return (_jsxs("div", { className: "param-editor", children: [_jsxs("div", { className: "row", children: [_jsx("input", { className: "txt", placeholder: "key", value: k, onChange: (e) => setK(e.target.value) }), _jsx("input", { className: "txt", placeholder: "value", value: v, onChange: (e) => setV(e.target.value) }), _jsx("button", { className: "btn secondary", onClick: () => {
                            if (!k)
                                return;
                            onChange({ ...value, [k]: v });
                            setK('');
                            setV('');
                        }, children: "Add" })] }), pairs.length > 0 && (_jsx("ul", { className: "kv", children: pairs.map(([kk, vv]) => (_jsxs("li", { children: [_jsx("code", { children: kk }), "=", _jsx("code", { children: vv }), _jsx("button", { className: "icon-btn", title: "remove", onClick: () => {
                                const n = { ...value };
                                delete n[kk];
                                onChange(n);
                            }, children: "\u2715" })] }, kk))) }))] }));
}
