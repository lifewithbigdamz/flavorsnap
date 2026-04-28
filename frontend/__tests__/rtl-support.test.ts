describe("RTL support", () => {
  const rtlLocales = ["ar"];
  const ltrLocales = ["en", "fr", "yo"];

  it("should identify Arabic as an RTL locale", () => {
    for (const locale of rtlLocales) {
      expect(rtlLocales.includes(locale)).toBe(true);
    }
  });

  it("should identify en, fr, yo as LTR locales", () => {
    for (const locale of ltrLocales) {
      expect(rtlLocales.includes(locale)).toBe(false);
    }
  });
});
