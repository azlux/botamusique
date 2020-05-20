const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  entry: {
    main: [
        './src/js/app.js',
        './src/sass/app.scss',
    ],
  },
  output: {
    filename: 'assets/js/[name].js',
    path: path.resolve(__dirname, 'build/'),
    //ecmaVersion: 5,
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: 'assets/css/[name].css',
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
    rules: [
      {
        test: /\.s[ac]ss$/i,
        use: [
          MiniCssExtractPlugin.loader,
          'css-loader',
          'sass-loader'
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
          },
        },
      },
    ],
  },
  /*experiments: {
    mjs: true,
  },*/
};