import React from 'react';
export const pretty = value => JSON.stringify(value, null, 2);
export const Form = ({title, children, onSubmit}) => <form className="panel" onSubmit={e => {e.preventDefault();onSubmit(new FormData(e.currentTarget));}}><h3>{title}</h3>{children}</form>;
export const Field = ({label,...props}) => <label>{label}<input {...props}/></label>;
export const Choice = ({label,children,...props}) => <label>{label}<select {...props}>{children}</select></label>;
export const options = rows => rows.map(r => <option key={r.id} value={r.id}>{r.name || r.id}</option>);
export const Badge = ({value}) => <span className={`badge ${value?.toLowerCase()}`}>{value}</span>;
export const Details = ({value}) => <pre className="details">{pretty(value)}</pre>;
