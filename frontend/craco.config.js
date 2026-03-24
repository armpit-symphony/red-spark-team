module.exports = {
  style: {
    postcss: {
      mode: 'extends',
    },
  },
  devServer: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
};
