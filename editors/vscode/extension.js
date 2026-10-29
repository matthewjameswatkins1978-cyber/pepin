'use strict';

const { spawn, execFile } = require('node:child_process');
const path = require('node:path');

const MAX_OUTPUT_BYTES = 4 * 1024 * 1024;
const VALID_STATUSES = new Set(['valid', 'incomplete', 'invalid']);

function byteOffsetToUtf16(source, wantedByteOffset) {
  if (!Number.isInteger(wantedByteOffset) || wantedByteOffset < 0) {
    throw new Error('Compiler returned an invalid UTF-8 byte offset');
  }
  let byteOffset = 0;
  let utf16Offset = 0;
  for (const character of source) {
    if (byteOffset >= wantedByteOffset) return utf16Offset;
    const width = Buffer.byteLength(character, 'utf8');
    if (byteOffset + width > wantedByteOffset) {
      throw new Error('Compiler span ends inside a UTF-8 character');
    }
    byteOffset += width;
    utf16Offset += character.length;
  }
  if (byteOffset === wantedByteOffset) return utf16Offset;
  throw new Error('Compiler byte offset is outside the document');
}

function parseCompilerResult(stdout, source) {
  let result;
  try {
    result = JSON.parse(stdout.trim());
  } catch {
    throw new Error('Pep CLI did not return valid JSON');
  }
  if (!result || result.schemaVersion !== 2 || !VALID_STATUSES.has(result.status) || !Array.isArray(result.diagnostics)) {
    throw new Error('Pep CLI returned an unsupported check response');
  }

  const diagnostics = result.diagnostics.map((item) => {
    if (!item || typeof item.message !== 'string' || typeof item.code !== 'string' || !item.span?.start) {
      throw new Error('Pep CLI returned a malformed diagnostic');
    }
    const start = byteOffsetToUtf16(source, item.span.start.offset);
    const end = byteOffsetToUtf16(source, item.span.endOffset);
    if (end < start) throw new Error('Pep CLI returned a reversed diagnostic span');
    return { start, end, message: item.message, code: item.code, severity: 'error' };
  });

  if (result.status === 'incomplete') {
    if (!Array.isArray(result.holes)) throw new Error('Pep CLI omitted typed-hole facts');
    for (const hole of result.holes) {
      if (!hole?.span?.start || (hole.identity !== null && typeof hole.identity !== 'string')) {
        throw new Error('Pep CLI returned a malformed typed-hole fact');
      }
      const start = byteOffsetToUtf16(source, hole.span.start.offset);
      const end = byteOffsetToUtf16(source, hole.span.endOffset);
      if (end < start) throw new Error('Pep CLI returned a reversed typed-hole span');
      const identity = hole.identity ?? '';
      const expected = hole.expectedType ? ` (expected ${hole.expectedType})` : '';
      diagnostics.push({
        start,
        end,
        message: `Unfilled typed hole ?${identity}${expected}`,
        code: 'PEP_TYPED_HOLE',
        severity: 'warning'
      });
    }
  }
  return diagnostics;
}

function activate(context) {
  const vscode = require('vscode');
  const output = vscode.window.createOutputChannel('Pep');
  const collection = vscode.languages.createDiagnosticCollection('pep');
  const running = new Map();

  function stop(uri) {
    const key = uri.toString();
    const task = running.get(key);
    if (!task) return;
    clearTimeout(task.timer);
    if (task.child.pid && process.platform === 'win32') {
      execFile('taskkill.exe', ['/pid', String(task.child.pid), '/t', '/f'], { windowsHide: true }, (error) => {
        if (error) task.child.kill();
      });
    } else if (task.child.pid) {
      try { process.kill(-task.child.pid, 'SIGTERM'); } catch { task.child.kill(); }
    } else {
      task.child.kill();
    }
    running.delete(key);
  }

  function findCli(document) {
    const config = vscode.workspace.getConfiguration('pep', document.uri);
    const configured = config.get('cliPath', '').trim();
    const folder = vscode.workspace.getWorkspaceFolder(document.uri);
    if (configured) return path.resolve(folder?.uri.fsPath || process.cwd(), configured);
    if (!folder) return undefined;
    const root = folder.uri.fsPath;
    let current = path.dirname(document.uri.fsPath);
    while (true) {
      const candidate = path.join(current, 'pep.ps1');
      try {
        if (require('node:fs').statSync(candidate).isFile()) return candidate;
      } catch { /* Continue toward the workspace root. */ }
      if (current === root || !current.startsWith(root + path.sep)) break;
      current = path.dirname(current);
    }
    return undefined;
  }

  function check(document) {
    if (document.languageId !== 'pep' || document.isDirty || document.uri.scheme !== 'file') return;
    stop(document.uri);
    const cli = findCli(document);
    if (!cli) {
      collection.delete(document.uri);
      output.appendLine(`No pep.ps1 found for ${document.uri.fsPath}; set pep.cliPath to configure it.`);
      return;
    }
    const config = vscode.workspace.getConfiguration('pep', document.uri);
    const powershell = config.get('powershellPath', 'pwsh');
    const timeoutMs = config.get('checkTimeoutMs', 20000);
    const child = spawn(powershell, ['-NoLogo', '-NoProfile', '-File', cli, 'check', document.uri.fsPath, '--json'], {
      cwd: path.dirname(cli),
      windowsHide: true,
      shell: false,
      detached: process.platform !== 'win32',
      env: process.env
    });
    const task = { child, timer: undefined, stdout: '', stderr: '' };
    running.set(document.uri.toString(), task);
    task.timer = setTimeout(() => {
      output.appendLine(`Timed out checking ${document.uri.fsPath}`);
      stop(document.uri);
    }, timeoutMs);
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', (part) => {
      task.stdout += part;
      if (Buffer.byteLength(task.stdout, 'utf8') > MAX_OUTPUT_BYTES) {
        output.appendLine(`Pep check output exceeded 4 MiB for ${document.uri.fsPath}`);
        stop(document.uri);
      }
    });
    child.stderr.on('data', (part) => { task.stderr += part; });
    child.on('error', (error) => {
      if (running.get(document.uri.toString()) !== task) return;
      clearTimeout(task.timer);
      running.delete(document.uri.toString());
      collection.delete(document.uri);
      output.appendLine(`Could not start Pep CLI: ${error.message}`);
    });
    child.on('close', () => {
      if (running.get(document.uri.toString()) !== task) return;
      clearTimeout(task.timer);
      running.delete(document.uri.toString());
      if (document.isClosed || document.isDirty) return;
      try {
        const mapped = parseCompilerResult(task.stdout, document.getText());
        const diagnostics = mapped.map((item) => {
          const diagnostic = new vscode.Diagnostic(
            new vscode.Range(document.positionAt(item.start), document.positionAt(item.end)),
            item.message,
            item.severity === 'error' ? vscode.DiagnosticSeverity.Error : vscode.DiagnosticSeverity.Warning
          );
          diagnostic.source = 'Pep';
          diagnostic.code = item.code;
          return diagnostic;
        });
        collection.set(document.uri, diagnostics);
        if (task.stderr.trim()) output.appendLine(task.stderr.trim());
      } catch (error) {
        collection.delete(document.uri);
        output.appendLine(`Pep check failed for ${document.uri.fsPath}: ${error.message}`);
        if (task.stderr.trim()) output.appendLine(task.stderr.trim());
      }
    });
  }

  const checkOpen = (document) => {
    const enabled = vscode.workspace.getConfiguration('pep', document.uri).get('lintOnOpen', true);
    if (enabled) check(document);
  };
  context.subscriptions.push(output, collection);
  context.subscriptions.push(vscode.workspace.onDidOpenTextDocument(checkOpen));
  context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(check));
  context.subscriptions.push(vscode.workspace.onDidChangeTextDocument(({ document }) => {
    stop(document.uri);
    collection.delete(document.uri);
  }));
  context.subscriptions.push(vscode.workspace.onDidCloseTextDocument((document) => {
    stop(document.uri);
    collection.delete(document.uri);
  }));
  for (const document of vscode.workspace.textDocuments) checkOpen(document);
}

function deactivate() {}

module.exports = { activate, deactivate, byteOffsetToUtf16, parseCompilerResult };