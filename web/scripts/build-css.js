const sass = require('node-sass');
const fs = require('fs');

sass.render({
    file: './src/sass/main.scss',
    outFile: './build/assets/css/main.min.css',
    outputStyle: 'compressed',
}, function (error, result) {
    if (error) {
        console.error(error);
    }
    
    // No errors during compilation, write the result to disk
    fs.writeFile('./build/assets/css/main.min.css', result.css, function (err) {
        if (err) {
            console.error(err);
        }

        console.info('CSS compiled.');
    });
});