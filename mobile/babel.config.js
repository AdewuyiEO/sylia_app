module.exports = function (api) {
  api.cache(true);
  return {
    // babel-preset-expo adds the reanimated/worklets plugin itself.
    presets: ['babel-preset-expo'],
  };
};
