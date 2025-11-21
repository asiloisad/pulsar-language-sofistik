const { provideKeywords } = require('./provider')

module.exports = {
  provideKeywords() {
    return {
      name: 'sofistik-keywords',
      version: '1.0.0',
      provider: provideKeywords()
    };
  }
};
