const REM_ROOT_VALUE = 100;

export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
    'postcss-pxtorem': {
      // Keep this value aligned with ROOT_FONT_BASE in src/config/responsive.ts.
      rootValue: REM_ROOT_VALUE,
      propList: ['*'],
      selectorBlackList: ['.norem'],
      replace: true,
      mediaQuery: false,
      minPixelValue: 1,
      exclude: /node_modules/i,
    },
  },
};
