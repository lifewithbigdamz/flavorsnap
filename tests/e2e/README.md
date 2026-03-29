# FlavorSnap E2E Tests

Comprehensive end-to-end tests for the FlavorSnap food classification application using Cypress.

## 📋 Test Coverage

### Test Suites

1. **01-homepage.cy.js** - Homepage and navigation tests
   - Page loading and rendering
   - Branding and UI elements
   - Responsive design verification
   - SEO meta tags

2. **02-image-upload.cy.js** - Image upload functionality
   - File selection via input
   - Drag and drop upload
   - Image preview
   - File type validation
   - Multiple upload handling

3. **03-classification.cy.js** - Core classification features
   - Successful classification workflow
   - Loading states
   - Confidence scores display
   - Error handling
   - API integration

4. **04-api-integration.cy.js** - Backend API tests
   - Health check endpoints
   - Classification API
   - Error responses
   - Rate limiting
   - CORS headers

5. **05-user-experience.cy.js** - Complete user journeys
   - Full classification workflow
   - Error recovery
   - State management
   - Multiple sessions
   - Offline handling

6. **06-responsive-design.cy.js** - Cross-device compatibility
   - Mobile, tablet, desktop viewports
   - Touch-friendly interfaces
   - Layout adaptation
   - Orientation changes

7. **07-accessibility.cy.js** - WCAG compliance
   - Keyboard navigation
   - Screen reader support
   - ARIA attributes
   - Color contrast
   - Focus management

8. **08-performance.cy.js** - Performance optimization
   - Page load times
   - Classification speed
   - Memory management
   - Caching strategies
   - Bundle size

## 🚀 Running Tests

### Prerequisites

```bash
# Install Cypress and dependencies
npm install --save-dev cypress @cypress/webpack-dev-server cypress-file-upload

# Or if using the frontend directory
cd frontend
npm install --save-dev cypress @cypress/webpack-dev-server cypress-file-upload
```

### Run All Tests

```bash
# Headless mode (CI/CD)
npx cypress run

# Interactive mode (development)
npx cypress open
```

### Run Specific Test Suite

```bash
# Run single test file
npx cypress run --spec "tests/e2e/03-classification.cy.js"

# Run multiple test files
npx cypress run --spec "tests/e2e/01-homepage.cy.js,tests/e2e/02-image-upload.cy.js"
```

### Run with Different Browsers

```bash
# Chrome
npx cypress run --browser chrome

# Firefox
npx cypress run --browser firefox

# Edge
npx cypress run --browser edge
```

### Run with Custom Configuration

```bash
# Custom base URL
npx cypress run --config baseUrl=http://localhost:3001

# Custom viewport
npx cypress run --config viewportWidth=1920,viewportHeight=1080

# Disable video recording
npx cypress run --config video=false
```

## 🐳 Docker Testing

Run tests in Docker environment:

```bash
# Using docker-compose
docker-compose -f docker-compose.test.yml up e2e-tests

# View test results
docker-compose -f docker-compose.test.yml logs e2e-tests
```

## 📊 Test Reports

### HTML Reports

After running tests, view the HTML report:

```bash
# Open the report
open test-results/e2e/index.html
```

### Screenshots and Videos

- Screenshots: `tests/e2e/screenshots/`
- Videos: `tests/e2e/videos/`
- Downloads: `tests/e2e/downloads/`

## 🔧 Configuration

### Environment Variables

Set in `cypress.config.js` or via command line:

```bash
# API URLs
CYPRESS_apiUrl=http://localhost:5000
CYPRESS_apiV1Url=http://localhost:8000/api/v1

# Base URL
CYPRESS_baseUrl=http://localhost:3000
```

### Custom Commands

Custom Cypress commands are defined in `tests/e2e/support/commands.js`:

- `cy.uploadFile()` - Upload file to input
- `cy.waitForApiResponse()` - Wait for API response
- `cy.verifyClassification()` - Verify classification results
- `cy.checkApiHealth()` - Check API health
- `cy.mockClassification()` - Mock API response
- `cy.clearAppData()` - Clear storage and cookies
- `cy.checkResponsive()` - Test responsive design
- `cy.screenshotWithTimestamp()` - Take timestamped screenshot

## 📝 Writing New Tests

### Test Structure

```javascript
/// <reference types="cypress" />

describe("Feature Name", () => {
  beforeEach(() => {
    cy.clearAppData();
    cy.visit("/");
    cy.waitForPageLoad();
  });

  it("should do something", () => {
    // Test implementation
  });
});
```

### Best Practices

1. **Use data-testid attributes** for reliable selectors
2. **Mock API responses** for consistent tests
3. **Clean up state** between tests
4. **Use custom commands** for common operations
5. **Add meaningful assertions** with clear error messages
6. **Handle async operations** properly with cy.wait()
7. **Test error scenarios** not just happy paths
8. **Keep tests independent** - no dependencies between tests

### Example Test

```javascript
it("should classify food image", () => {
  // Arrange
  cy.fixture("test-responses.json").then((responses) => {
    cy.mockClassification(responses.successfulClassification);
  });

  // Act
  cy.uploadFile("test-food.jpg");
  cy.contains("button", /classify/i).click();

  // Assert
  cy.verifyClassification("Moi Moi", 85);
});
```

## 🐛 Debugging

### Debug Mode

```bash
# Run with debug output
DEBUG=cypress:* npx cypress run

# Open DevTools in interactive mode
npx cypress open --browser chrome --config chromeWebSecurity=false
```

### Common Issues

1. **Timeout errors**: Increase timeout in cypress.config.js
2. **Element not found**: Use better selectors or add data-testid
3. **Flaky tests**: Add proper waits and assertions
4. **API errors**: Check if backend is running

### Troubleshooting

```bash
# Clear Cypress cache
npx cypress cache clear

# Verify Cypress installation
npx cypress verify

# Check Cypress info
npx cypress info
```

## 📈 CI/CD Integration

### GitHub Actions

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: cypress-io/github-action@v5
        with:
          start: npm start
          wait-on: "http://localhost:3000"
          browser: chrome
```

### GitLab CI

```yaml
e2e-tests:
  image: cypress/browsers:latest
  script:
    - npm ci
    - npm start &
    - npx wait-on http://localhost:3000
    - npx cypress run --browser chrome
  artifacts:
    when: always
    paths:
      - tests/e2e/screenshots/
      - tests/e2e/videos/
```

## 📚 Resources

- [Cypress Documentation](https://docs.cypress.io/)
- [Cypress Best Practices](https://docs.cypress.io/guides/references/best-practices)
- [Cypress API Reference](https://docs.cypress.io/api/table-of-contents)
- [FlavorSnap Documentation](../../README.md)

## 🤝 Contributing

When adding new tests:

1. Follow the existing test structure
2. Add descriptive test names
3. Include comments for complex logic
4. Update this README with new test coverage
5. Ensure tests pass locally before committing

## 📄 License

Same as FlavorSnap project - MIT License
