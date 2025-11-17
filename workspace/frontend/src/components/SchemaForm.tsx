// workspace/frontend/src/components/SchemaForm.tsx
import React from 'react';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

const ajv = addFormats(new Ajv({ allErrors: true, strict: false }));

type JSONSchema = any;

export default function SchemaForm({
  schema,
  value,
  onChange
}: {
  schema?: JSONSchema;
  value: any;
  onChange: (v: any) => void;
}) {
  if (!schema) {
    return (
      <textarea
        className="txtarea"
        placeholder="JSON body"
        value={safeStringify(value)}
        onChange={(e) => trySet(e.target.value, onChange)}
      />
    );
  }

  // Простая форма: если объект, рендерим поля; иначе raw JSON
  if (schema.type === 'object' && schema.properties) {
    const props = schema.properties as Record<string, any>;
    const required: string[] = schema.required || [];

    return (
      <div className="form">
        {Object.entries(props).map(([key, propSchema]) => (
          <Field
            key={key}
            name={key}
            required={required.includes(key)}
            schema={propSchema}
            value={value?.[key]}
            onChange={(v) => onChange({ ...(value || {}), [key]: v })}
          />
        ))}
      </div>
    );
  }

  return (
    <textarea
      className="txtarea"
      placeholder="JSON body"
      value={safeStringify(value)}
      onChange={(e) => trySet(e.target.value, onChange)}
    />
  );
}

function Field({
  name,
  required,
  schema,
  value,
  onChange
}: {
  name: string;
  required: boolean;
  schema: any;
  value: any;
  onChange: (v: any) => void;
}) {
  const type = Array.isArray(schema.type) ? schema.type[0] : schema.type;

  if (type === 'string' || type === 'number' || type === 'integer') {
    return (
      <label className="row">
        <span className="lbl">
          {name} {required && <span className="req">*</span>}
        </span>
        <input
          className="txt"
          type={type === 'string' ? 'text' : 'number'}
          value={value ?? ''}
          onChange={(e) =>
            onChange(type === 'string' ? e.target.value : Number(e.target.value))
          }
          placeholder={schema.description || ''}
        />
      </label>
    );
  }

  if (type === 'boolean') {
    return (
      <label className="row">
        <span className="lbl">
          {name} {required && <span className="req">*</span>}
        </span>
        <input
          className="chk"
          type="checkbox"
          checked={!!value}
          onChange={(e) => onChange(e.target.checked)}
        />
      </label>
    );
  }

  if (type === 'array') {
    const items = Array.isArray(value) ? value : [];
    return (
      <div className="block">
        <h5>
          {name} {required && <span className="req">*</span>}
        </h5>
        {items.map((it: any, idx: number) => (
          <div key={idx} className="row">
            <input
              className="txt"
              value={String(it ?? '')}
              onChange={(e) => {
                const next = [...items];
                next[idx] = e.target.value;
                onChange(next);
              }}
            />
            <button
              className="icon-btn"
              onClick={() => {
                const next = items.filter((_: any, i: number) => i !== idx);
                onChange(next);
              }}
            >
              ✕
            </button>
          </div>
        ))}
        <button className="btn secondary" onClick={() => onChange([...(items || []), ''])}>
          + item
        </button>
      </div>
    );
  }

  // Fallback: raw JSON
  return (
    <div className="block">
      <label className="row">
        <span className="lbl">
          {name} {required && <span className="req">*</span>}
        </span>
      </label>
      <textarea
        className="txtarea"
        value={safeStringify(value)}
        onChange={(e) => trySet(e.target.value, onChange)}
      />
    </div>
  );
}

function safeStringify(v: any) {
  try {
    return typeof v === 'string' ? v : JSON.stringify(v ?? {}, null, 2);
  } catch {
    return '';
  }
}

function trySet(text: string, set: (v: any) => void) {
  try {
    set(JSON.parse(text));
  } catch {
    set(text);
  }
}
