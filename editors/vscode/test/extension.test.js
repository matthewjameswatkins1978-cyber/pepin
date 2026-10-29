'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { byteOffsetToUtf16, parseCompilerResult } = require('../extension');

const root = path.resolve(__dirname, '..');

test('maps Pep UTF-8 byte offsets to VS Code UTF-16 positions', () => {
  const source = '# 🐇\r\nlet x: Int = "bad"';
  const startByte = Buffer.byteLength('# 🐇\r\nlet x: Int = ', 'utf8');
  const result = parseCompilerResult(JSON.stringify({
    schemaVersion: 2,
    status: 'invalid',
    diagnostics: [{
      code: 'PEP_TYPE_MISMATCH',
      message: 'Expected Int but found Str',
      span: { start: { offset: startByte }, endOffset: startByte + Buffer.byteLength('"bad"', 'utf8') }
    }]
  }), source);
  assert.deepEqual(result, [{
    start: source.indexOf('"bad"'),
    end: source.indexOf('"bad"') + '"bad"'.length,
    message: 'Expected Int but found Str',
    code: 'PEP_TYPE_MISMATCH',
    severity: 'error'
  }]);
  assert.equal(byteOffsetToUtf16('🐇x', 4), 2);
});

test('uses compiler hole facts for incomplete-program warnings', () => {
  const source = 'fn f() -> Int { return ?todo }';
  const result = parseCompilerResult(JSON.stringify({
    schemaVersion: 2,
    status: 'incomplete',
    diagnostics: [],
    holes: [{ identity: 'todo', expectedType: 'Int', span: { start: { offset: 23 }, endOffset: 28 } }]
  }), source);
  assert.equal(result.length, 1);
  assert.equal(result[0].code, 'PEP_TYPED_HOLE');
  assert.equal(result[0].severity, 'warning');
  assert.equal(source.slice(result[0].start, result[0].end), '?todo');
});

test('supports unnamed typed holes reported by the compiler', () => {
  const source = 'fn f() -> Int { return ? }';
  const start = source.indexOf('?');
  const result = parseCompilerResult(JSON.stringify({
    schemaVersion: 2,
    status: 'incomplete',
    diagnostics: [],
    holes: [{ identity: null, expectedType: 'Int', span: { start: { offset: start }, endOffset: start + 1 } }]
  }), source);
  assert.equal(result[0].message, 'Unfilled typed hole ? (expected Int)');
  assert.equal(source.slice(result[0].start, result[0].end), '?');
});

test('rejects missing or unsupported compiler contracts instead of guessing', () => {
  assert.throws(() => parseCompilerResult('not json', 'x'), /valid JSON/);
  assert.throws(() => parseCompilerResult(JSON.stringify({ schemaVersion: 3, status: 'valid', diagnostics: [] }), ''), /unsupported/);
  assert.throws(() => parseCompilerResult(JSON.stringify({ schemaVersion: 2, status: 'incomplete', diagnostics: [] }), ''), /typed-hole facts/);
});

test('extension manifest and syntax grammar are valid JSON and registered for .pep', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  const grammar = JSON.parse(fs.readFileSync(path.join(root, 'syntaxes', 'pep.tmLanguage.json'), 'utf8'));
  const language = JSON.parse(fs.readFileSync(path.join(root, 'language-configuration.json'), 'utf8'));
  assert.equal(manifest.contributes.languages[0].extensions[0], '.pep');
  assert.equal(manifest.contributes.grammars[0].scopeName, 'source.pep');
  assert.ok(grammar.repository.keywords.match.includes('match'));
  assert.ok(grammar.repository.strings.begin);
  assert.ok(new RegExp(grammar.repository.holes.match).test('_'));
  assert.ok(language.brackets.some(([open, close]) => open === '{' && close === '}'));
});