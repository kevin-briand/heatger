const path = require('path')

module.exports = [
  {
    mode: 'production',
    entry: './dist/panel/heatger-panel.js',
    output: {
      filename: 'heatger-panel.js',
      path: path.resolve(__dirname, 'dist')
    }
  }
]
