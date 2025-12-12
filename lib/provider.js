/**
 * SOFiSTiK Keywords Service Provider
 *
 * Provides programmatic access to SOFiSTiK keywords for other packages
 * and tools in the Pulsar ecosystem.
 *
 * Supports version-specific and language-specific keyword loading with lazy caching.
 * Also provides version detection from file content and sofistik.def.
 */

const path = require("path");
const fs = require("fs");

class SofistikKeywordsProvider {
  constructor() {
    // Cache for transformed keywords: { "2026.en": {...}, "2025.de": {...} }
    this.cache = {};
    // Merged data cache per language: { "en": {...}, "de": {...} }
    this.mergedData = {};
    this.commandsPath = path.join(__dirname, "..", "commands");
    this.defaultVersion = "2026";
    this.defaultLanguage = "en";
    // Map config values to language codes
    this.languageMap = { english: "en", german: "de", en: "en", de: "de" };
  }

  /**
   * Load the merged JSON file for a specific language (lazy, cached)
   * @param {string} language - Language code (en or de)
   * @returns {Object} Merged keywords data
   */
  loadMerged(language = "en") {
    if (this.mergedData[language]) {
      return this.mergedData[language];
    }

    const mergedPath = path.join(this.commandsPath, `sofistik.${language}.json`);
    try {
      if (fs.existsSync(mergedPath)) {
        const data = fs.readFileSync(mergedPath, "utf8");
        this.mergedData[language] = JSON.parse(data);
        return this.mergedData[language];
      }
    } catch (error) {
      console.error(`Error loading merged SOFiSTiK keywords (${language}):`, error);
    }

    this.mergedData[language] = { _meta: { versions: [], default: this.defaultVersion } };
    return this.mergedData[language];
  }

  /**
   * Normalize language value to code (en/de)
   * @param {string} lang - Language value from config or detection
   * @returns {string} Normalized language code (en or de)
   */
  normalizeLanguage(lang) {
    if (!lang) return null;
    return this.languageMap[lang.toLowerCase()] || null;
  }

  /**
   * Detect SOFiSTiK version and language from editor content or sofistik.def file
   * @param {TextEditor} editor - Optional editor to check
   * @param {string} filePath - Optional file path to check sofistik.def
   * @returns {{version: string|null, language: string|null}} Detected version and language
   */
  detect(editor, filePath) {
    let version = null;
    let language = null;

    // Determine the target path for sofistik.def lookup
    let targetPath = filePath;
    if (!targetPath && editor) {
      targetPath = editor.getPath();
    }

    // 1. Try to detect from first line of editor (shebang: @ SOFiSTiK YYYY)
    // Only use editor shebang if it's the same file as target
    const editorPath = editor ? editor.getPath() : null;
    const sameFile = !targetPath || !editorPath ||
      path.normalize(editorPath).toLowerCase() === path.normalize(targetPath).toLowerCase();
    if (editor && sameFile) {
      try {
        // Only check the first line for shebang
        const firstLine = editor.lineTextForBufferRow(0);
        const match = firstLine.match(/^@\s*SOFiSTiK\s+(\d{4})(?:-\d{1,2})?(?:\s+(EN|DE))?/i);
        if (match) {
          version = match[1];
          if (match[2]) {
            language = match[2].toLowerCase();
          }
        }
      } catch (e) {
        // Ignore errors
      }
    }

    // 2. Try to detect from sofistik.def in the same directory as the file
    if (!version && targetPath) {
      const defPath = path.join(path.dirname(targetPath), "sofistik.def");
      if (fs.existsSync(defPath)) {
        try {
          const defContent = fs.readFileSync(defPath, "utf8");
          const match = defContent.match(/^\s*SOF_VERSION\s*=\s*(\d{4})/m);
          if (match) {
            version = match[1];
          }
        } catch (e) {
          // Silently ignore read errors
        }
      }
    }

    return { version, language };
  }

  /**
   * Detect SOFiSTiK version from editor content or sofistik.def file
   * @param {TextEditor} editor - Optional editor to check
   * @param {string} filePath - Optional file path to check sofistik.def
   * @returns {string|null} Detected version or null
   * @deprecated Use detect() instead
   */
  detectVersion(editor, filePath) {
    return this.detect(editor, filePath).version;
  }

  /**
   * Get version with fallback to config
   * @param {string} version - Optional explicit version
   * @param {TextEditor} editor - Optional editor for detection
   * @param {string} filePath - Optional file path for detection
   * @returns {string} Version string
   */
  getVersion(version, editor, filePath) {
    if (!version) {
      version = this.detect(editor, filePath).version;
    }
    if (!version) {
      // Check language-sofistik config
      const configVersion = atom.config.get("language-sofistik.version");
      if (configVersion && configVersion !== "Auto") {
        version = configVersion;
      }
    }
    if (!version) {
      version = this.defaultVersion;
    }
    return version;
  }

  /**
   * Get language with fallback to config
   * @param {string} language - Optional explicit language
   * @param {TextEditor} editor - Optional editor for detection
   * @param {string} filePath - Optional file path for detection
   * @returns {string} Language code (en or de)
   */
  getLanguage(language, editor, filePath) {
    if (!language) {
      language = this.detect(editor, filePath).language;
    }
    if (!language) {
      // Check language-sofistik config
      const configLanguage = atom.config.get("language-sofistik.language");
      if (configLanguage) {
        language = this.normalizeLanguage(configLanguage);
      }
    }
    if (!language) {
      language = this.defaultLanguage;
    }
    return language;
  }

  /**
   * Resolve version and language for a given context
   * @param {TextEditor} editor - Optional editor for detection
   * @param {string} filePath - Optional file path for detection
   * @returns {{version: string, language: string}} Resolved version and language
   */
  resolve(editor, filePath) {
    const detected = this.detect(editor, filePath);

    let version = detected.version;
    if (!version) {
      const configVersion = atom.config.get("language-sofistik.version");
      if (configVersion && configVersion !== "Auto") {
        version = configVersion;
      }
    }
    version = version || this.defaultVersion;

    let language = detected.language;
    if (!language) {
      const configLanguage = atom.config.get("language-sofistik.language");
      if (configLanguage) {
        language = this.normalizeLanguage(configLanguage);
      }
    }
    language = language || this.defaultLanguage;

    return { version, language };
  }

  /**
   * Check if a command is available in the given version
   * @param {Object} cmd - Command entry from merged data
   * @param {string} version - Target version
   * @param {string[]} allVersions - All available versions
   * @returns {boolean} True if command is available
   */
  isCommandInVersion(cmd, version, allVersions) {
    if (!cmd.v) return true; // No version restriction = all versions

    const v = cmd.v;
    if (v.includes("-")) {
      // Range: "2020-2024"
      const [start, end] = v.split("-");
      const startIdx = allVersions.indexOf(start);
      const endIdx = allVersions.indexOf(end);
      const verIdx = allVersions.indexOf(version);
      return verIdx >= startIdx && verIdx <= endIdx;
    } else if (v.includes(",")) {
      // List: "2020,2022,2024"
      return v.split(",").includes(version);
    } else {
      // Single version onwards: "2020" means 2020+
      const startIdx = allVersions.indexOf(v);
      const verIdx = allVersions.indexOf(version);
      return verIdx >= startIdx;
    }
  }

  /**
   * Load keywords from merged JSON file (with caching and transformation)
   * @param {string} version - SOFiSTiK version (2018, 2020, 2022, 2024, 2025, 2026)
   * @param {string} language - Language code (en, de)
   * @returns {Object} Keywords object for the version/language
   */
  loadKeywords(version, language) {
    // Normalize inputs
    version = version || this.defaultVersion;
    language = language || this.defaultLanguage;

    const cacheKey = `${version}.${language}`;

    // Return from cache if available
    if (this.cache[cacheKey]) {
      return this.cache[cacheKey];
    }

    // Load language-specific merged file
    const merged = this.loadMerged(language);
    const allVersions = merged._meta?.versions || [];

    // Validate version
    if (!allVersions.includes(version)) {
      console.warn(
        `SOFiSTiK version ${version} not found, falling back to ${this.defaultVersion}`
      );
      version = this.defaultVersion;
    }

    // Transform merged data to format: { MODULE: { CMD: { PARAM: enums } } }
    const result = {};

    for (const [moduleName, moduleData] of Object.entries(merged)) {
      if (moduleName.startsWith("_")) continue; // Skip _meta

      result[moduleName] = {};

      for (const [cmdName, cmdData] of Object.entries(moduleData)) {
        // Check version availability
        if (!this.isCommandInVersion(cmdData, version, allVersions)) {
          continue;
        }

        // Get params (or empty object if none)
        result[moduleName][cmdName] = cmdData.params || {};
      }
    }

    this.cache[cacheKey] = result;
    return result;
  }

  /**
   * Get keywords for the resolved version/language based on editor context
   * @param {TextEditor} editor - Optional editor for detection
   * @param {string} filePath - Optional file path for detection
   * @returns {Object} Complete keywords object organized by module
   */
  getKeywords(editor, filePath) {
    const { version, language } = this.resolve(editor, filePath);
    return this.loadKeywords(version, language);
  }

  /**
   * Get keywords for a specific version and language
   * @param {string} version - SOFiSTiK version
   * @param {string} language - Language code
   * @returns {Object} Complete keywords object organized by module
   */
  getKeywordsFor(version, language) {
    return this.loadKeywords(version, language);
  }

  /**
   * Get keywords for a specific module
   * @param {string} moduleName - Name of the module (e.g., 'AQUA', 'SOFILOAD')
   * @param {TextEditor} editor - Optional editor for detection
   * @param {string} filePath - Optional file path for detection
   * @returns {Object|null} Module keywords or null if not found
   */
  getModuleKeywords(moduleName, editor, filePath) {
    const keywords = this.getKeywords(editor, filePath);
    return keywords[moduleName] || null;
  }

  /**
   * Get all module names
   * @param {TextEditor} editor - Optional editor for detection
   * @param {string} filePath - Optional file path for detection
   * @returns {string[]} Array of module names
   */
  getModuleNames(editor, filePath) {
    const keywords = this.getKeywords(editor, filePath);
    return Object.keys(keywords);
  }

  /**
   * Get all commands for a specific module
   * @param {string} moduleName - Name of the module
   * @param {TextEditor} editor - Optional editor for detection
   * @param {string} filePath - Optional file path for detection
   * @returns {string[]} Array of command names
   */
  getModuleCommands(moduleName, editor, filePath) {
    const module = this.getModuleKeywords(moduleName, editor, filePath);
    return module ? Object.keys(module) : [];
  }

  /**
   * Get sub-keywords (params object) for a specific command in a module
   * @param {string} moduleName - Name of the module
   * @param {string} commandName - Name of the command
   * @param {TextEditor} editor - Optional editor for detection
   * @param {string} filePath - Optional file path for detection
   * @returns {Object|null} Params object {paramName: [enums] or null} or null if not found
   */
  getCommandKeywords(moduleName, commandName, editor, filePath) {
    const module = this.getModuleKeywords(moduleName, editor, filePath);
    return module && module[commandName] ? module[commandName] : null;
  }

  /**
   * Get parameter names for a specific command
   * @param {string} moduleName - Name of the module
   * @param {string} commandName - Name of the command
   * @param {TextEditor} editor - Optional editor for detection
   * @param {string} filePath - Optional file path for detection
   * @returns {string[]} Array of parameter names
   */
  getCommandParams(moduleName, commandName, editor, filePath) {
    const params = this.getCommandKeywords(moduleName, commandName, editor, filePath);
    return params ? Object.keys(params) : [];
  }

  /**
   * Get enum values for a specific parameter
   * @param {string} moduleName - Name of the module
   * @param {string} commandName - Name of the command
   * @param {string} paramName - Name of the parameter
   * @param {TextEditor} editor - Optional editor for detection
   * @param {string} filePath - Optional file path for detection
   * @returns {string[]|null} Array of enum values or null
   */
  getParamEnums(moduleName, commandName, paramName, editor, filePath) {
    const params = this.getCommandKeywords(moduleName, commandName, editor, filePath);
    if (params && paramName in params) {
      return params[paramName];
    }
    return null;
  }

  /**
   * Search for a keyword across all modules
   * @param {string} keyword - Keyword to search for
   * @param {TextEditor} editor - Optional editor for detection
   * @param {string} filePath - Optional file path for detection
   * @returns {Object[]} Array of results with module, command, and type information
   */
  searchKeyword(keyword, editor, filePath) {
    const keywords = this.getKeywords(editor, filePath);
    const results = [];
    const searchTerm = keyword.toUpperCase();

    for (const [moduleName, module] of Object.entries(keywords)) {
      for (const [commandName, params] of Object.entries(module)) {
        if (commandName.toUpperCase().includes(searchTerm)) {
          results.push({
            module: moduleName,
            command: commandName,
            type: "command",
          });
        }

        // params is now an object: {paramName: [enums] or null}
        if (params) {
          for (const paramName of Object.keys(params)) {
            if (paramName.toUpperCase().includes(searchTerm)) {
              results.push({
                module: moduleName,
                command: commandName,
                keyword: paramName,
                type: "param",
              });
            }
          }
        }
      }
    }

    return results;
  }

  /**
   * Get statistics about the keywords
   * @param {TextEditor} editor - Optional editor for detection
   * @param {string} filePath - Optional file path for detection
   * @returns {Object} Statistics object
   */
  getStatistics(editor, filePath) {
    const { version, language } = this.resolve(editor, filePath);
    const keywords = this.getKeywords(editor, filePath);

    const stats = {
      version,
      language,
      totalModules: 0,
      totalCommands: 0,
      totalSubKeywords: 0,
      moduleStats: {},
    };

    for (const [moduleName, module] of Object.entries(keywords)) {
      stats.totalModules++;
      const commandCount = Object.keys(module).length;
      // params is now an object: {paramName: [enums] or null}
      const subKeywordCount = Object.values(module).reduce(
        (sum, params) => sum + (params ? Object.keys(params).length : 0),
        0
      );

      stats.totalCommands += commandCount;
      stats.totalSubKeywords += subKeywordCount;

      stats.moduleStats[moduleName] = {
        commands: commandCount,
        subKeywords: subKeywordCount,
      };
    }

    return stats;
  }

  /**
   * Validate if a word is a SOFiSTiK keyword
   * @param {string} word - Word to validate
   * @param {TextEditor} editor - Optional editor for detection
   * @param {string} filePath - Optional file path for detection
   * @returns {Object|null} Match information or null if not a keyword
   */
  validateKeyword(word, editor, filePath) {
    const keywords = this.getKeywords(editor, filePath);
    const searchTerm = word.toUpperCase();

    for (const [moduleName, module] of Object.entries(keywords)) {
      // Check if it's a command name
      if (module[searchTerm]) {
        return {
          module: moduleName,
          command: searchTerm,
          type: "command",
          params: module[searchTerm],
        };
      }

      // Check if it's a parameter name within a command
      for (const [commandName, params] of Object.entries(module)) {
        if (params && searchTerm in params) {
          return {
            module: moduleName,
            command: commandName,
            keyword: searchTerm,
            type: "param",
            enumValues: params[searchTerm],
          };
        }
      }
    }

    return null;
  }

  /**
   * Get available versions
   * @returns {string[]} Array of available version strings
   */
  getAvailableVersions() {
    const merged = this.loadMerged();
    return merged._meta?.versions || [];
  }

  /**
   * Clear the keywords cache
   */
  clearCache() {
    this.cache = {};
    this.mergedData = null;
  }
}

// Singleton instance
let providerInstance = null;

// Export the service provider
module.exports = {
  SofistikKeywordsProvider,

  /**
   * Create and return a keywords provider instance (singleton)
   * @returns {SofistikKeywordsProvider}
   */
  provideKeywords() {
    if (!providerInstance) {
      providerInstance = new SofistikKeywordsProvider();
    }
    return providerInstance;
  },

  /**
   * Get the singleton provider instance
   * @returns {SofistikKeywordsProvider|null}
   */
  getProvider() {
    return providerInstance;
  },
};
