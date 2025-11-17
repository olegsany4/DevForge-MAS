import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
const ajv = addFormats(new Ajv({ allErrors: true, strict: false }));
export default function SchemaForm({ schema, value, onChange }) {
    if (!schema) {
        return (_jsx("textarea", { className: "txtarea", placeholder: "JSON body", value: safeStringify(value), onChange: (e) => trySet(e.target.value, onChange) }));
    }
    // Простая форма: если объект, рендерим поля; иначе raw JSON
    if (schema.type === 'object' && schema.properties) {
        const props = schema.properties;
        const required = schema.required || [];
        return (_jsx("div", { className: "form", children: Object.entries(props).map(([key, propSchema]) => (_jsx(Field, { name: key, required: required.includes(key), schema: propSchema, value: value?.[key], onChange: (v) => onChange({ ...(value || {}), [key]: v }) }, key))) }));
    }
    return (_jsx("textarea", { className: "txtarea", placeholder: "JSON body", value: safeStringify(value), onChange: (e) => trySet(e.target.value, onChange) }));
}
function Field({ name, required, schema, value, onChange }) {
    const type = Array.isArray(schema.type) ? schema.type[0] : schema.type;
    if (type === 'string' || type === 'number' || type === 'integer') {
        return (_jsxs("label", { className: "row", children: [_jsxs("span", { className: "lbl", children: [name, " ", required && _jsx("span", { className: "req", children: "*" })] }), _jsx("input", { className: "txt", type: type === 'string' ? 'text' : 'number', value: value ?? '', onChange: (e) => onChange(type === 'string' ? e.target.value : Number(e.target.value)), placeholder: schema.description || '' })] }));
    }
    if (type === 'boolean') {
        return (_jsxs("label", { className: "row", children: [_jsxs("span", { className: "lbl", children: [name, " ", required && _jsx("span", { className: "req", children: "*" })] }), _jsx("input", { className: "chk", type: "checkbox", checked: !!value, onChange: (e) => onChange(e.target.checked) })] }));
    }
    if (type === 'array') {
        const items = Array.isArray(value) ? value : [];
        return (_jsxs("div", { className: "block", children: [_jsxs("h5", { children: [name, " ", required && _jsx("span", { className: "req", children: "*" })] }), items.map((it, idx) => (_jsxs("div", { className: "row", children: [_jsx("input", { className: "txt", value: String(it ?? ''), onChange: (e) => {
                                const next = [...items];
                                next[idx] = e.target.value;
                                onChange(next);
                            } }), _jsx("button", { className: "icon-btn", onClick: () => {
                                const next = items.filter((_, i) => i !== idx);
                                onChange(next);
                            }, children: "\u2715" })] }, idx))), _jsx("button", { className: "btn secondary", onClick: () => onChange([...(items || []), '']), children: "+ item" })] }));
    }
    // Fallback: raw JSON
    return (_jsxs("div", { className: "block", children: [_jsx("label", { className: "row", children: _jsxs("span", { className: "lbl", children: [name, " ", required && _jsx("span", { className: "req", children: "*" })] }) }), _jsx("textarea", { className: "txtarea", value: safeStringify(value), onChange: (e) => trySet(e.target.value, onChange) })] }));
}
function safeStringify(v) {
    try {
        return typeof v === 'string' ? v : JSON.stringify(v ?? {}, null, 2);
    }
    catch {
        return '';
    }
}
function trySet(text, set) {
    try {
        set(JSON.parse(text));
    }
    catch {
        set(text);
    }
}
