# language-sofistik

Syntax highlighting for SOFiSTiK with optimized grammar and programmatic keyword access.

- **Syntax Highlighting**: Complete syntax highlighting for SOFiSTiK files (`.dat`, `.gra`, `.grb`, `.results`)
- **RAW File Support**: Grammar for SOFiSTiK output files (`.erg`, `.lst`, `.prt`, `.urs`)
- **Keywords Service**: Programmatic access to SOFiSTiK keywords for other packages
- **Multi-Version Support**: Keywords for SOFiSTiK versions 2018-2026
- **Multi-Language Support**: English and German keyword sets

## Installation

To install `language-sofistik` search for [language-sofistik](https://web.pulsar-edit.dev/packages/language-sofistik) in the Install pane of the Pulsar settings or run `ppm install language-sofistik`. Alternatively, you can run `ppm install asiloisad/pulsar-language-sofistik` to install a package directly from the GitHub repository.

## Configuration

- **SOFiSTiK Version**: Select a specific version (2018-2026) or let it be detected automatically
- **Language**: Choose between English and German keyword sets

### Version Detection

The package detects the SOFiSTiK version from:

1. **File shebang** (first line): `@ SOFiSTiK 2026` or `@ SOFiSTiK 2026 EN`
2. **sofistik.def file** in the same directory: `SOF_VERSION = 2026`
3. **Config setting**: If a specific version is selected
4. **Auto fallback**: Latest version

## SOFiSTiK Keywords Service

This package provides a service that exposes SOFiSTiK keywords for programmatic access by other Pulsar packages.

To use the SOFiSTiK keywords service in your package, add to your `package.json`:

```json
{
  "consumedServices": {
    "sofistik.keywords": {
      "versions": {
        "2.0.0": "consumeKeywords"
      }
    }
  }
}
```

Then implement the consumer in your package's main file:

```javascript
module.exports = {
  keywordsService: null,

  consumeKeywords(service) {
    this.keywordsService = service.provider;
  },
};
```

### Creating a Context

Create a context-bound provider using `withContext()`. The context resolves version and language once at creation, so subsequent method calls don't need to pass editor/filePath:

```javascript
// Create context from editor (detects version/language from file)
const ctx = this.keywordsService.withContext(editor);

// Or from file path
const ctx = this.keywordsService.withContext(null, "/path/to/file.dat");

// Or use defaults from config
const ctx = this.keywordsService.withContext();

// Then use methods without passing context each time
const keywords = ctx.getKeywords();
const modules = ctx.getModuleNames();
const commands = ctx.getModuleCommands("AQUA");
```

### Context Methods

#### `getVersion()` / `getLanguage()`

Get the resolved version and language for this context.

```javascript
const version = ctx.getVersion(); // "2026"
const language = ctx.getLanguage(); // "en"
```

#### `getKeywords()`

Returns the complete keywords object organized by module.

```javascript
const keywords = ctx.getKeywords();
// Returns: { "AQUA": { "BEAM": { "NO": null, "NPA": null, ... }, ... }, ... }
```

#### `getModuleKeywords(moduleName)`

Get keywords for a specific module.

```javascript
const aquaKeywords = ctx.getModuleKeywords("AQUA");
// Returns: { "BEAM": { "NO": null, ... }, "ECHO": { ... }, ... }
```

#### `getModuleNames()`

Get all module names.

```javascript
const modules = ctx.getModuleNames();
// Returns: ["AQUA", "SOFILOAD", "SOFIMSHA", ...]
```

#### `getModuleCommands(moduleName)`

Get all commands for a specific module.

```javascript
const commands = ctx.getModuleCommands("AQUA");
// Returns: ["BEAM", "ECHO", "TRUS", ...]
```

#### `getCommandKeywords(moduleName, commandName)`

Get parameters object for a specific command.

```javascript
const beamParams = ctx.getCommandKeywords("AQUA", "BEAM");
// Returns: { "NO": null, "NPA": null, "TYPE": ["B", "T", "V", ...], ... }
```

#### `getCommandParams(moduleName, commandName)`

Get parameter names for a specific command.

```javascript
const params = ctx.getCommandParams("AQUA", "BEAM");
// Returns: ["NO", "NPA", "TYPE", "HINB", ...]
```

#### `getParamEnums(moduleName, commandName, paramName)`

Get enum values for a specific parameter.

```javascript
const enums = ctx.getParamEnums("AQUA", "BEAM", "TYPE");
// Returns: ["B", "T", "V", ...] or null if no enums
```

#### `searchKeyword(keyword)`

Search for a keyword across all modules.

```javascript
const results = ctx.searchKeyword("BEAM");
// Returns: [
//   { module: "AQUA", command: "BEAM", type: "command" },
//   { module: "SOFIMSHA", command: "NODE", keyword: "BEAM", type: "param" },
//   ...
// ]
```

#### `validateKeyword(word)`

Validate if a word is a SOFiSTiK keyword.

```javascript
const validation = ctx.validateKeyword("BEAM");
// Returns: {
//   module: "AQUA",
//   command: "BEAM",
//   type: "command",
//   params: { "NO": null, "NPA": null, ... }
// }

const paramValidation = ctx.validateKeyword("TYPE");
// Returns: {
//   module: "AQUA",
//   command: "BEAM",
//   keyword: "TYPE",
//   type: "param",
//   enumValues: ["B", "T", "V", ...]
// }
```

#### `getStatistics()`

Get statistics about the keywords.

```javascript
const stats = ctx.getStatistics();
// Returns: {
//   version: "2026",
//   language: "en",
//   totalModules: 25,
//   totalCommands: 450,
//   totalSubKeywords: 2800,
//   moduleStats: {
//     "AQUA": { commands: 45, subKeywords: 320 },
//     ...
//   }
// }
```

### Provider Methods

These methods are available directly on the provider (without creating a context):

#### `getAvailableVersions()`

Get all available SOFiSTiK versions.

```javascript
const versions = this.keywordsService.getAvailableVersions();
// Returns: ["2018", "2020", "2022", "2023", "2024", "2025", "2026"]
```

#### `loadKeywords(version, language)`

Load keywords for a specific version and language directly.

```javascript
const keywords = this.keywordsService.loadKeywords("2024", "de");
```

# Contributing

Got ideas to make this package better, found a bug, or want to help add new features? Just drop your thoughts on GitHub — any feedback's welcome!
