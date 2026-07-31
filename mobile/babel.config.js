module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    // reanimated's plugin MUST be listed last.
    plugins: ['react-native-reanimated/plugin'],
  };
};
