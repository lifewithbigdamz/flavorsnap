/* eslint-disable @typescript-eslint/no-require-imports */
import fs from "fs";
import path from "path";

const i18nConfig = require("../next-i18next.config");

describe("next-i18next configuration", () => {
  it("should have 'en' as the default locale", () => {
    expect(i18nConfig.i18n.defaultLocale).toBe("en");
  });

  it("should support en, fr, ar, and yo locales", () => {
    expect(i18nConfig.i18n.locales).toEqual(["en", "fr", "ar", "yo"]);
  });

  it("should have translation files for every configured locale", () => {
    const localesDir = path.resolve(__dirname, "../public/locales");
    for (const locale of i18nConfig.i18n.locales) {
      const filePath = path.join(localesDir, locale, "common.json");
      expect(fs.existsSync(filePath)).toBe(true);
    }
  });
});

describe("translation files", () => {
  const localesDir = path.resolve(__dirname, "../public/locales");
  const enTranslations = JSON.parse(
    fs.readFileSync(path.join(localesDir, "en", "common.json"), "utf-8"),
  );
  const enKeys = Object.keys(enTranslations);

  const otherLocales = ["fr", "ar", "yo"];

  it.each(otherLocales)(
    "locale '%s' should have all keys from the English translation",
    (locale) => {
      const translations = JSON.parse(
        fs.readFileSync(path.join(localesDir, locale, "common.json"), "utf-8"),
      );
      const keys = Object.keys(translations);
      expect(keys).toEqual(enKeys);
    },
  );

  it.each(otherLocales)(
    "locale '%s' should have no empty translation values",
    (locale) => {
      const translations = JSON.parse(
        fs.readFileSync(path.join(localesDir, locale, "common.json"), "utf-8"),
      );
      for (const [, value] of Object.entries(translations)) {
        expect(value).not.toBe("");
      }
    },
  );
});
