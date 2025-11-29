const { CompositeDisposable } = require("atom");
const { provideKeywords } = require("./provider");

/**
 * Language SOFiSTiK Package
 *
 * Provides SOFiSTiK syntax highlighting via unified grammar (source.sofistik).
 * Keywords are resolved dynamically based on file content or config settings.
 */
module.exports = {
  activate() {
    this.disposables = new CompositeDisposable();
    this.provider = provideKeywords();
  },

  deactivate() {
    this.disposables.dispose();
  },

  /**
   * Provide keywords service for other packages
   * @returns {Object} Service object with provider
   */
  provideKeywords() {
    return {
      name: "sofistik-keywords",
      version: "2.0.0",
      provider: provideKeywords(),
    };
  },
};
