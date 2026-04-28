import { render, screen } from "@testing-library/react";
import LanguageSwitcher from "@/components/LanguageSwitcher";

// Mock next/router
const mockPush = jest.fn();
jest.mock("next/router", () => ({
  useRouter: () => ({
    locale: "en",
    locales: ["en", "fr", "ar", "yo"],
    pathname: "/",
    asPath: "/",
    query: {},
    push: mockPush,
  }),
}));

// Mock next-i18next
jest.mock("next-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        select_language: "Language",
      };
      return translations[key] || key;
    },
  }),
}));

describe("LanguageSwitcher", () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it("renders the language selector", () => {
    render(<LanguageSwitcher />);
    expect(screen.getByLabelText("Language")).toBeInTheDocument();
  });

  it("renders all 4 locale options", () => {
    render(<LanguageSwitcher />);
    const select = screen.getByLabelText("Language") as HTMLSelectElement;
    expect(select.options).toHaveLength(4);
  });

  it("has English selected by default", () => {
    render(<LanguageSwitcher />);
    const select = screen.getByLabelText("Language") as HTMLSelectElement;
    expect(select.value).toBe("en");
  });

  it("displays correct labels for each locale", () => {
    render(<LanguageSwitcher />);
    const options = screen.getAllByRole("option");
    const labels = options.map((opt) => opt.textContent);
    expect(labels).toEqual(["English", "Français", "العربية", "Yorùbá"]);
  });
});
