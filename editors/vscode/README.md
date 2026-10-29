# Pep language support for VS Code

This extension associates `.pep` files with Pep, provides TextMate syntax colors, indentation and bracket behavior, and reports diagnostics from the repository's `pep.ps1 check FILE --json` command.

## Use it

Open the Pepin repository (or a folder containing `pep.ps1`) in VS Code and open a `.pep` file. Saved files are checked when opened and after each save. The extension never runs Pep programs. By default it locates `pep.ps1` by walking upward from the file, bounded by the open workspace, then calls PowerShell 7 (`pwsh`). Set `pep.cliPath` or `pep.powershellPath` if your setup needs explicit paths.

To try the extension from this checkout, open `editors/vscode` in VS Code and press **F5** to launch an Extension Development Host. In that new window, open the Pepin repository and then a `.pep` file. For regular installation, package the extension as a VSIX and install that artifact through VS Code.

Diagnostics are produced only from schema-v2 compiler JSON. Compiler errors become error diagnostics; compiler-reported typed holes become warnings. If the CLI cannot run or returns malformed JSON, details go to the **Pep** output channel and no guessed language diagnostics are shown. Files are checked only after save, since the current CLI accepts a file path rather than unsaved document contents.

The syntax grammar is a presentation layer for editor coloring. Parsing, type checking, hole facts, and diagnostic locations remain owned by the Pep compiler. There is no second Pep parser or LSP implementation. The diagnostics adapter is kept independent of VS Code APIs so it can later be reused by an LSP client.

## ChatGPT-compatible examples

ChatGPT's native Markdown renderer does not install extension grammars. Use a labeled fenced block to preserve Pep source clearly:

```pep
fn double(value: Int) -> Int {
    return value * 2
}

say(int_text(double(21)))
```

The `pep` label identifies the language for compatible renderers; ChatGPT may show it as an ordinary monospaced block without Pep colors. For accurate local colorization, open the same source in VS Code with this extension.

## Development

Run the extension's dependency-free adapter and manifest tests from this directory with `npm test`. Package the extension with the normal VS Code Extension Manager tooling (`vsce package`) when distributing it. No VS Code or Node packages are required by the runtime extension itself.