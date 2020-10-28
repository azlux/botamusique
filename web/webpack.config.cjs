const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  mode: 'production',
  entry: {
    main: [
      './js/app.mjs',
      './sass/app.scss',
    ],
    dark: [
      './sass/app-dark.scss',
    ],
  },
  devtool: 'source-map',
  output: {
    filename: 'static/js/[name].js',
    path: path.resolve(__dirname, '../'),
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: 'static/css/[name].css',
    }),
    new HtmlWebpackPlugin({
      filename: 'templates/index.template.html',
      template: './templates/index.template.html',
      inject: false,
    }),
    new HtmlWebpackPlugin({
      filename: 'templates/need_token.template.html',
      template: './templates/need_token.template.html',
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
          loader: 'postcss-loader',
          options: {
            postcssOptions: {
              plugins: [
                [
                  'autoprefixer',
                  {
                    // Options
                  },
                ],
              ],
            },
          },
        },
        'sass-loader', // compiles Sass to CSS
      ],
    },
    {
      test: /\.m?js$/,
      exclude: /(node_modules|bower_components)/,
      resolve: {
        fullySpecified: false,
      },
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
};
