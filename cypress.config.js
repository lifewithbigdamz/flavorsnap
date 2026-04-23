const { defineConfig } = require("cypress");

module.exports = defineConfig({
  e2e: {
    baseUrl: "http://localhost:3000",
    supportFile: "tests/e2e/support/e2e.js",
    specPattern: "tests/e2e/**/*.cy.{js,jsx,ts,tsx}",
    fixturesFolder: "tests/e2e/fixtures",
    screenshotsFolder: "tests/e2e/screenshots",
    videosFolder: "tests/e2e/videos",
    downloadsFolder: "tests/e2e/downloads",

    setupNodeEvents(on, config) {
      // implement node event listeners here
      on("task", {
        log(message) {
          console.log(message);
          return null;
        },
      });
    },

    // Test configuration
    viewportWidth: 1280,
    viewportHeight: 720,
    defaultCommandTimeout: 10000,
    requestTimeout: 10000,
    responseTimeout: 10000,
    pageLoadTimeout: 30000,

    // Video and screenshot settings
    video: true,
    videoCompression: 32,
    screenshotOnRunFailure: true,

    // Retry configuration
    retries: {
      runMode: 2,
      openMode: 0,
    },

    // Environment variables
    env: {
      apiUrl: "http://localhost:5000",
      apiV1Url: "http://localhost:8000/api/v1",
    },
  },

  component: {
    devServer: {
      framework: "next",
      bundler: "webpack",
    },
    specPattern: "frontend/**/*.cy.{js,jsx,ts,tsx}",
  },
});
