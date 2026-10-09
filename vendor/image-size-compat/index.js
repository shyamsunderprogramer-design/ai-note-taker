const modern = require('image-size-modern');
module.exports = Object.assign((...args) => modern.imageSize(...args), modern);
