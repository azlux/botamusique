const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  entry: {
    main: [
      './src/js/app.mjs',
      './src/sass/app.scss',
    ],
    dark: [
      './src/sass/app-dark.scss',
    ],
  },
  devtool: 'source-map',
  output: {
    filename: 'static/js/[name].js',
    path: path.resolve(__dirname, '../'),
    // ecmaVersion: 5,
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: 'static/css/[name].css',
    }),
    new HtmlWebpackPlugin({
      filename: 'templates/index.html',
      template: './src/templates/index.html',
      inject: false,
    }),
    new HtmlWebpackPlugin({
      filename: 'templates/need_token.html',
      template: './src/templates/need_token.html',
      inject: false,
    }),
  ],
  module: {
    rules: [{
      test: /\.s[ac]ss$/i,
      use: [
        MiniCssExtractPlugin.loader,
        'css-loader', // translates CSS into CommonJS modules
        {
          loader: 'postcss-loader', // Run postcss actions
          options: {
            plugins: function() { // postcss plugins, can be exported to postcss.config.js
              return [
                require('autoprefixer'),
              ];
            },
          },
        },
        'sass-loader', // compiles Sass to CSS
      ],
    },
    {
      test: /\.m?js$/,
      exclude: /(node_modules|bower_components)/,
      use: {
        loader: 'babel-loader',
        options: {
          presets: [
            [
              '@babel/preset-env',
              {
                'corejs': '3.6',
                'useBuiltIns': 'usage',
              },
            ],
          ],
          plugins: [
            '@babel/plugin-proposal-class-properties',
          ],
        },
      },
    },
    ],
  },
  /* experiments: {
    mjs: true,
  },*/
};
