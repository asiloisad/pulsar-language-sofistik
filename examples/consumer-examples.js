/**
 * Example: Consumer Package for SOFiSTiK Keywords Service
 * 
 * This is a complete example of how to create a package that consumes
 * the SOFiSTiK keywords service.
 */

// ============================================================================
// Example 1: Basic Consumer Package
// ============================================================================

// package.json
const examplePackageJson = {
  "name": "sofistik-helper",
  "main": "./lib/main",
  "version": "1.0.0",
  "description": "Helper tools for SOFiSTiK development",
  "consumedServices": {
    "sofistik.keywords": {
      "versions": {
        "1.0.0": "consumeKeywords"
      }
    }
  }
};

// lib/main.js
const exampleMain = {
  keywordsProvider: null,

  activate() {
    console.log('SOFiSTiK Helper activated');
  },

  deactivate() {
    this.keywordsProvider = null;
  },

  consumeKeywords(service) {
    // Store the provider for later use
    this.keywordsProvider = service.provider;
    
    // Log some statistics
    const stats = this.keywordsProvider.getStatistics();
    console.log('Loaded SOFiSTiK keywords:');
    console.log(`  Modules: ${stats.totalModules}`);
    console.log(`  Commands: ${stats.totalCommands}`);
    console.log(`  Sub-keywords: ${stats.totalSubKeywords}`);
    
    // Example: List all modules
    const modules = this.keywordsProvider.getModuleNames();
    console.log('Available modules:', modules.join(', '));
  },

  // Example method using the keywords provider
  searchForKeyword(keyword) {
    if (!this.keywordsProvider) {
      console.error('Keywords provider not available');
      return [];
    }

    return this.keywordsProvider.searchKeyword(keyword);
  }
};

// ============================================================================
// Example 2: Autocomplete Provider
// ============================================================================

class SofistikAutocompleteProvider {
  constructor(keywordsProvider) {
    this.provider = keywordsProvider;
    this.selector = '.source.sofistik';
    this.disableForSelector = '.source.sofistik .comment';
    this.inclusionPriority = 1;
    this.suggestionPriority = 2;
  }

  getSuggestions({ editor, bufferPosition, scopeDescriptor, prefix }) {
    // Only provide suggestions if prefix is at least 2 characters
    if (prefix.length < 2) {
      return [];
    }

    // Search for keywords matching the prefix
    const results = this.provider.searchKeyword(prefix);
    
    // Convert to autocomplete suggestions
    return results.map(result => {
      const suggestion = {
        text: result.command || result.keyword,
        displayText: result.command || result.keyword,
        type: result.type === 'command' ? 'keyword' : 'function',
        leftLabel: result.module,
        description: `${result.module} ${result.type}`
      };

      // Add detailed info for commands
      if (result.type === 'command') {
        const commandInfo = this.provider.getCommandKeywords(
          result.module,
          result.command
        );
        if (commandInfo && commandInfo.length > 0) {
          suggestion.descriptionMoreURL = `data:text/plain,Sub-keywords: ${commandInfo.join(', ')}`;
        }
      }

      return suggestion;
    });
  }
}

// In your main.js:
const autocompleteExample = {
  keywordsProvider: null,
  autocompleteProvider: null,

  consumeKeywords(service) {
    this.keywordsProvider = service.provider;
    this.autocompleteProvider = new SofistikAutocompleteProvider(
      this.keywordsProvider
    );
  },

  provideAutocomplete() {
    return this.autocompleteProvider;
  }
};

// ============================================================================
// Example 3: Linter Integration
// ============================================================================

class SofistikLinter {
  constructor(keywordsProvider) {
    this.provider = keywordsProvider;
    this.grammarScopes = ['source.sofistik'];
    this.scope = 'file';
    this.lintsOnChange = true;
  }

  lint(textEditor) {
    const text = textEditor.getText();
    const messages = [];

    // Extract potential keywords (simplified)
    const wordPattern = /\b[A-Z]{2,}\b/g;
    let match;

    while ((match = wordPattern.exec(text)) !== null) {
      const word = match[0];
      const validation = this.provider.validateKeyword(word);

      // Check if it's a known keyword
      if (!validation) {
        const position = textEditor.getBuffer().positionForCharacterIndex(match.index);
        
        // Search for similar keywords
        const suggestions = this.provider.searchKeyword(word.substring(0, 3));
        const suggestionText = suggestions.length > 0
          ? ` Did you mean: ${suggestions[0].command || suggestions[0].keyword}?`
          : '';

        messages.push({
          severity: 'warning',
          location: {
            file: textEditor.getPath(),
            position: [position, position]
          },
          excerpt: `Unknown SOFiSTiK keyword: ${word}${suggestionText}`
        });
      }
    }

    return messages;
  }
}

// ============================================================================
// Example 4: Command Palette Integration
// ============================================================================

const commandPaletteExample = {
  keywordsProvider: null,

  consumeKeywords(service) {
    this.keywordsProvider = service.provider;

    // Register commands
    atom.commands.add('atom-workspace', {
      'sofistik:show-module-info': () => this.showModuleInfo(),
      'sofistik:search-keyword': () => this.searchKeywordDialog(),
      'sofistik:show-statistics': () => this.showStatistics()
    });
  },

  showModuleInfo() {
    const modules = this.keywordsProvider.getModuleNames();
    const stats = this.keywordsProvider.getStatistics();

    let content = 'SOFiSTiK Modules:\\n\\n';
    modules.forEach(module => {
      const moduleStats = stats.moduleStats[module];
      content += `${module}: ${moduleStats.commands} commands, ${moduleStats.subKeywords} sub-keywords\\n`;
    });

    atom.notifications.addInfo('SOFiSTiK Modules', {
      detail: content,
      dismissable: true
    });
  },

  async searchKeywordDialog() {
    const keyword = await this.promptForKeyword();
    if (!keyword) return;

    const results = this.keywordsProvider.searchKeyword(keyword);
    
    if (results.length === 0) {
      atom.notifications.addWarning(`No matches found for: ${keyword}`);
      return;
    }

    let content = `Found ${results.length} matches for "${keyword}":\\n\\n`;
    results.forEach(result => {
      content += `${result.module} - ${result.command || result.keyword} (${result.type})\\n`;
    });

    atom.notifications.addSuccess('Search Results', {
      detail: content,
      dismissable: true
    });
  },

  showStatistics() {
    const stats = this.keywordsProvider.getStatistics();
    
    const content = `
Total Modules: ${stats.totalModules}
Total Commands: ${stats.totalCommands}
Total Sub-keywords: ${stats.totalSubKeywords}

Average commands per module: ${Math.round(stats.totalCommands / stats.totalModules)}
Average sub-keywords per module: ${Math.round(stats.totalSubKeywords / stats.totalModules)}
    `.trim();

    atom.notifications.addInfo('SOFiSTiK Statistics', {
      detail: content,
      dismissable: true
    });
  },

  promptForKeyword() {
    return new Promise((resolve) => {
      const panel = atom.workspace.addModalPanel({
        item: document.createElement('div')
      });
      
      const input = document.createElement('input');
      input.type = 'text';
      input.placeholder = 'Enter keyword to search...';
      input.style.width = '100%';
      input.style.padding = '10px';
      
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          panel.destroy();
          resolve(input.value);
        } else if (e.key === 'Escape') {
          panel.destroy();
          resolve(null);
        }
      });
      
      panel.getItem().appendChild(input);
      input.focus();
    });
  }
};

// ============================================================================
// Export examples for reference
// ============================================================================

module.exports = {
  examplePackageJson,
  exampleMain,
  autocompleteExample,
  SofistikAutocompleteProvider,
  SofistikLinter,
  commandPaletteExample
};
