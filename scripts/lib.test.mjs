// node scripts/lib.test.mjs
import assert from 'node:assert/strict';
import { spokenText } from './lib.mjs';

assert.equal(spokenText('  Into the *lehr*  now. '), 'Into the lehr now.');
assert.equal(spokenText('Into the *lehr*.', { lehr: 'leer' }), 'Into the leer.');
assert.equal(spokenText('The LEHR, not the lehrs.', { lehr: 'leer' }), 'The leer, not the lehrs.');
assert.equal(spokenText('It hits 1,600 °C today.', { '1,600 °C': 'sixteen hundred degrees Celsius' }), 'It hits sixteen hundred degrees Celsius today.');
console.log('ok');
