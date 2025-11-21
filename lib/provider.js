/**
 * SOFiSTiK Keywords Service Provider
 *
 * Provides programmatic access to SOFiSTiK keywords for other packages
 * and tools in the Pulsar ecosystem.
 */

const path = require('path');
const fs = require('fs');

class SofistikKeywordsProvider {
  constructor() {
    this.keywords = null;
    this.loadKeywords();
  }

  /**
   * Load keywords from keywords.json
   */
  loadKeywords() {
    try {
      const keywordsPath = path.join(__dirname, '..', 'assets', 'keywords.json');
      const data = fs.readFileSync(keywordsPath, 'utf8');
      this.keywords = JSON.parse(data);
    } catch (error) {
      console.error('Error loading SOFiSTiK keywords:', error);
      this.keywords = {};
    }
  }

  /**
   * Get all keywords
   * @returns {Object} Complete keywords object organized by module
   */
  getKeywords() {
    return this.keywords;
  }

  /**
   * Get keywords for a specific module
   * @param {string} moduleName - Name of the module (e.g., 'AQUA', 'SOFILOAD')
   * @returns {Object|null} Module keywords or null if not found
   */
  getModuleKeywords(moduleName) {
    return this.keywords[moduleName] || null;
  }

  /**
   * Get all module names
   * @returns {string[]} Array of module names
   */
  getModuleNames() {
    return Object.keys(this.keywords);
  }

  /**
   * Get all commands for a specific module
   * @param {string} moduleName - Name of the module
   * @returns {string[]} Array of command names
   */
  getModuleCommands(moduleName) {
    const module = this.getModuleKeywords(moduleName);
    return module ? Object.keys(module) : [];
  }

  /**
   * Get sub-keywords for a specific command in a module
   * @param {string} moduleName - Name of the module
   * @param {string} commandName - Name of the command
   * @returns {string[]|null} Array of sub-keywords or null if not found
   */
  getCommandKeywords(moduleName, commandName) {
    const module = this.getModuleKeywords(moduleName);
    return module && module[commandName] ? module[commandName] : null;
  }

  /**
   * Search for a keyword across all modules
   * @param {string} keyword - Keyword to search for
   * @returns {Object[]} Array of results with module, command, and type information
   */
  searchKeyword(keyword) {
    const results = [];
    const searchTerm = keyword.toUpperCase();

    for (const [moduleName, module] of Object.entries(this.keywords)) {
      // Check commands
      for (const [commandName, subKeywords] of Object.entries(module)) {
        if (commandName.toUpperCase().includes(searchTerm)) {
          results.push({
            module: moduleName,
            command: commandName,
            type: 'command'
          });
        }

        // Check sub-keywords
        for (const subKeyword of subKeywords) {
          if (subKeyword.toUpperCase().includes(searchTerm)) {
            results.push({
              module: moduleName,
              command: commandName,
              keyword: subKeyword,
              type: 'sub-keyword'
            });
          }
        }
      }
    }

    return results;
  }

  /**
   * Get statistics about the keywords
   * @returns {Object} Statistics object
   */
  getStatistics() {
    const stats = {
      totalModules: 0,
      totalCommands: 0,
      totalSubKeywords: 0,
      moduleStats: {}
    };

    for (const [moduleName, module] of Object.entries(this.keywords)) {
      stats.totalModules++;
      const commandCount = Object.keys(module).length;
      const subKeywordCount = Object.values(module).reduce(
        (sum, keywords) => sum + keywords.length, 0
      );

      stats.totalCommands += commandCount;
      stats.totalSubKeywords += subKeywordCount;

      stats.moduleStats[moduleName] = {
        commands: commandCount,
        subKeywords: subKeywordCount
      };
    }

    return stats;
  }

  /**
   * Validate if a word is a SOFiSTiK keyword
   * @param {string} word - Word to validate
   * @returns {Object|null} Match information or null if not a keyword
   */
  validateKeyword(word) {
    const searchTerm = word.toUpperCase();

    for (const [moduleName, module] of Object.entries(this.keywords)) {
      // Check if it's a command
      if (module[searchTerm]) {
        return {
          module: moduleName,
          command: searchTerm,
          type: 'command',
          subKeywords: module[searchTerm]
        };
      }

      // Check if it's a sub-keyword
      for (const [commandName, subKeywords] of Object.entries(module)) {
        if (subKeywords.includes(searchTerm)) {
          return {
            module: moduleName,
            command: commandName,
            keyword: searchTerm,
            type: 'sub-keyword'
          };
        }
      }
    }

    return null;
  }
}

// Export the service provider
module.exports = {
  SofistikKeywordsProvider,

  /**
   * Create and return a keywords provider instance
   * @returns {SofistikKeywordsProvider}
   */
  provideKeywords() {
    return new SofistikKeywordsProvider();
  }
};
