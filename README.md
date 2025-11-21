# language-sofistik

Syntax highlighting for SOFiSTiK with optimized grammar and programmatic keyword access.

- **Syntax Highlighting**: Complete syntax highlighting for SOFiSTiK files (`.dat`, `.gra`, `.grb`, `.results`)
- **RAW File Support**: Grammar for SOFiSTiK output files (`.erg`, `.lst`, `.prt`, `.urs`)
- **Keywords Service**: Programmatic access to SOFiSTiK keywords for other packages

## Installation

To install `language-sofistik` search for [language-sofistik](https://web.pulsar-edit.dev/packages/language-sofistik) in the Install pane of the Pulsar settings or run `ppm install language-sofistik`. Alternatively, you can run `ppm install asiloisad/pulsar-language-sofistik` to install a package directly from the GitHub repository.

## Compatibility

Support versions of SOFiSTiK are 2026, 2025, 2024, 2023, 2022, 2020 and 2018. English only.

## SOFiSTiK Keywords Service

This package provides a service that exposes SOFiSTiK keywords for programmatic access by other Pulsar packages.

To use the SOFiSTiK keywords service in your package, add to your `package.json`:

```json
{
  "consumedServices": {
    "sofistik.keywords": {
      "versions": {
        "1.0.0": "consumeKeywords"
      }
    }
  }
}
```

Then implement the consumer in your package's main file:

```javascript
module.exports = {
  keywordsProvider: null,

  consumeKeywords(service) {
    this.keywordsProvider = service.provider;
  }
};
```

### `getKeywords()`
Returns the complete keywords object organized by module.

```javascript
const keywords = provider.getKeywords();
// Returns: { "AQUA": { "BEAM": [...], ... }, ... }
```

### `getModuleKeywords(moduleName)`
Get keywords for a specific module.

```javascript
const aquaKeywords = provider.getModuleKeywords('AQUA');
// Returns: { "BEAM": [...], "ECHO": [...], ... }
```

### `getModuleNames()`
Get all module names.

```javascript
const modules = provider.getModuleNames();
// Returns: ["AQUA", "SOFILOAD", "SOFIMSHA", ...]
```

### `getModuleCommands(moduleName)`
Get all commands for a specific module.

```javascript
const commands = provider.getModuleCommands('AQUA');
// Returns: ["BEAM", "ECHO", "TRUS", ...]
```

### `getCommandKeywords(moduleName, commandName)`
Get sub-keywords for a specific command.

```javascript
const beamKeywords = provider.getCommandKeywords('AQUA', 'BEAM');
// Returns: ["NO", "NPA", "TYPE", "HINB", ...]
```

### `searchKeyword(keyword)`
Search for a keyword across all modules.

```javascript
const results = provider.searchKeyword('BEAM');
// Returns: [
//   { module: "AQUA", command: "BEAM", type: "command" },
//   { module: "SOFiMSHA", command: "NODE", keyword: "BEAM", type: "sub-keyword" },
//   ...
// ]
```

### `validateKeyword(word)`
Validate if a word is a SOFiSTiK keyword.

```javascript
const validation = provider.validateKeyword('BEAM');
// Returns: {
//   module: "AQUA",
//   command: "BEAM",
//   type: "command",
//   subKeywords: ["NO", "NPA", ...]
// }
```

### `getStatistics()`
Get statistics about the keywords.

```javascript
const stats = provider.getStatistics();
// Returns: {
//   totalModules: 25,
//   totalCommands: 450,
//   totalSubKeywords: 2800,
//   moduleStats: {
//     "AQUA": { commands: 45, subKeywords: 320 },
//     ...
//   }
// }
```

### Build Grammar

The grammar is generated from `keywords.xlsx` using an optimized build script:

```bash
cd build
python build.py
```

This generates:
- `assets/keywords.json` - Keywords data for programmatic access
- `grammars/sofistik.cson` - Optimized grammar with reduced backtracking

# Contributing

Got ideas to make this package better, found a bug, or want to help add new features? Just drop your thoughts on GitHub — any feedback’s welcome!
