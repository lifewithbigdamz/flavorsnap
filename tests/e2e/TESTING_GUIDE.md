# E2E Testing Guide for FlavorSnap

## 🎯 Overview

This guide provides comprehensive information about the end-to-end testing strategy for FlavorSnap, including test organization, best practices, and troubleshooting.

## 📚 Test Organization

### Test Structure

```
tests/e2e/
├── 01-homepage.cy.js           # Homepage and navigation
├── 02-image-upload.cy.js       # Image upload functionality
├── 03-classification.cy.js     # Core classification features
├── 04-api-integration.cy.js    # Backend API integration
├── 05-user-experience.cy.js    # Complete user journeys
├── 06-responsive-design.cy.js  # Cross-device compatibility
├── 07-accessibility.cy.js      # WCAG compliance
├── 08-performance.cy.js        # Performance metrics
├── support/
│   ├── commands.js             # Custom Cypress commands
│   ├── e2e.js                  # Global configuration
│   └── utils.js                # Utility functions
├── fixtures/
│   ├── test-food.jpg           # Test image files
│   ├── test-responses.json     # Mock API responses
│   └── generate-test-image.js  # Image generator script
└── README.md                   # Test documentation
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Cypress and related packages
npm install --save-dev cypress cypress-file-upload

# Or install all project dependencies
npm install
```

### 2. Generate Test Fixtures

```bash
# Generate test images
node tests/e2e/fixtures/generate-test-image.js

# Or copy existing test images
cp test-food.jpg tests/e2e/fixtures/
```

### 3. Start Application Services

```bash
# Terminal 1: Start backend
cd ml-model-api
python app.py

# Terminal 2: Start frontend
cd frontend
npm run dev
```

### 4. Run Tests

```bash
# Interactive mode (recommended for development)
npm run test:e2e:open

# Headless mode (for CI/CD)
npm run test:e2e

# Specific browser
npm run test:e2e:chrome
npm run test:e2e:firefox
```

## 📋 Test Coverage

### User Journeys Covered

1. **Homepage Access**
   - Page loads successfully
   - All UI elements visible
   - Responsive on all devices
   - SEO meta tags present

2. **Image Upload**
   - File selection via input
   - Drag and drop upload
   - Image preview display
   - File type validation
   - Error handling

3. **Food Classification**
   - Successful classification
   - Loading states
   - Confidence scores
   - Multiple predictions
   - Error recovery

4. **API Integration**
   - Health checks
   - Classification endpoints
   - Error responses
   - Rate limiting
   - CORS handling

5. **User Experience**
   - Complete workflows
   - State management
   - Error recovery
   - Multiple sessions
   - Offline handling

6. **Responsive Design**
   - Mobile (375x667)
   - Tablet (768x1024)
   - Desktop (1280x720)
   - Large desktop (1920x1080)
   - Orientation changes

7. **Accessibility**
   - Keyboard navigation
   - Screen reader support
   - ARIA attributes
   - Focus management
   - Color contrast

8. **Performance**
   - Page load times
   - Classification speed
   - Memory management
   - Caching
   - Bundle optimization

## 🔧 Custom Commands

### File Upload

```javascript
// Upload a file from fixtures
cy.uploadFile("test-food.jpg", "image/jpeg");
```

### API Mocking

```javascript
// Mock successful classification
cy.fixture("test-responses.json").then((responses) => {
  cy.mockClassification(responses.successfulClassification);
});
```

### Classification Verification

```javascript
// Verify classification results
cy.verifyClassification("Moi Moi", 85);
```

### Responsive Testing

```javascript
// Test on different devices
cy.checkResponsive("mobile");
cy.checkResponsive("tablet");
cy.checkResponsive("desktop");
```

### API Health Check

```javascript
// Check if API is healthy
cy.checkApiHealth();
```

## 🎨 Writing Tests

### Test Template

```javascript
/// <reference types="cypress" />

describe("Feature Name", () => {
  beforeEach(() => {
    // Clean state before each test
    cy.clearAppData();
    cy.visit("/");
    cy.waitForPageLoad();
  });

  it("should perform expected behavior", () => {
    // Arrange: Set up test data and mocks
    cy.fixture("test-responses.json").then((responses) => {
      cy.mockClassification(responses.successfulClassification);
    });

    // Act: Perform user actions
    cy.uploadFile("test-food.jpg");
    cy.contains("button", /classify/i).click();

    // Assert: Verify expected outcomes
    cy.verifyClassification("Moi Moi", 85);
  });

  afterEach(() => {
    // Clean up if needed
  });
});
```

### Best Practices

1. **Use Descriptive Test Names**

   ```javascript
   ✅ it('should display error message when API fails')
   ❌ it('test error')
   ```

2. **Keep Tests Independent**

   ```javascript
   ✅ beforeEach(() => cy.clearAppData())
   ❌ Tests that depend on previous test state
   ```

3. **Use data-testid Attributes**

   ```javascript
   ✅ cy.get('[data-testid="upload-button"]')
   ❌ cy.get('.btn-primary.upload')
   ```

4. **Handle Async Operations**

   ```javascript
   ✅ cy.wait('@apiRequest')
   ❌ cy.wait(5000)
   ```

5. **Mock External Dependencies**
   ```javascript
   ✅ cy.mockClassification(mockData)
   ❌ Relying on actual API responses
   ```

## 🐛 Debugging

### Debug Mode

```bash
# Run with debug output
DEBUG=cypress:* npm run test:e2e

# Open DevTools
npm run test:e2e:open
```

### Common Issues

#### 1. Element Not Found

```javascript
// Problem
cy.get(".button").click(); // Fails if element doesn't exist

// Solution
cy.get(".button", { timeout: 10000 }).should("exist").click();
```

#### 2. Flaky Tests

```javascript
// Problem
cy.get(".result").should("contain", "Success"); // Might fail if slow

// Solution
cy.wait("@apiRequest");
cy.get(".result", { timeout: 10000 }).should("contain", "Success");
```

#### 3. API Not Available

```javascript
// Check API health before tests
before(() => {
  cy.checkApiHealth();
});
```

### Troubleshooting Commands

```bash
# Clear Cypress cache
npx cypress cache clear

# Verify installation
npx cypress verify

# Get system info
npx cypress info

# Run specific test
npx cypress run --spec "tests/e2e/03-classification.cy.js"
```

## 📊 Test Reports

### Viewing Results

```bash
# HTML report (after running tests)
open test-results/e2e/index.html

# Screenshots
ls tests/e2e/screenshots/

# Videos
ls tests/e2e/videos/
```

### CI/CD Integration

Tests automatically run on:

- Push to main/develop branches
- Pull requests
- Manual workflow dispatch

Results are uploaded as artifacts and available for 7 days.

## 🔒 Security Testing

### API Security

```javascript
it("should handle authentication", () => {
  cy.request({
    method: "POST",
    url: "/api/classify",
    failOnStatusCode: false,
  }).then((response) => {
    expect(response.status).to.be.oneOf([401, 403]);
  });
});
```

### Input Validation

```javascript
it("should reject malicious input", () => {
  const maliciousFile = new File(['<script>alert("xss")</script>'], "hack.jpg");
  // Test that app properly validates and sanitizes
});
```

## 📈 Performance Testing

### Metrics to Monitor

- Page load time: < 3 seconds
- Classification time: < 15 seconds
- First Contentful Paint: < 2 seconds
- Time to Interactive: < 5 seconds

### Performance Test Example

```javascript
it("should load page quickly", () => {
  const start = Date.now();
  cy.visit("/");
  cy.waitForPageLoad();
  const loadTime = Date.now() - start;
  expect(loadTime).to.be.lessThan(3000);
});
```

## 🌐 Cross-Browser Testing

### Supported Browsers

- Chrome (recommended)
- Firefox
- Edge
- Electron (default)

### Running on Different Browsers

```bash
# Chrome
npm run test:e2e:chrome

# Firefox
npm run test:e2e:firefox

# Edge
npx cypress run --browser edge
```

## 📱 Mobile Testing

### Device Emulation

```javascript
const devices = [
  { name: "iPhone SE", width: 375, height: 667 },
  { name: "iPad", width: 768, height: 1024 },
  { name: "Galaxy S20", width: 360, height: 800 },
];

devices.forEach((device) => {
  it(`should work on ${device.name}`, () => {
    cy.viewport(device.width, device.height);
    cy.visit("/");
    // Test mobile-specific features
  });
});
```

## 🔄 Continuous Integration

### GitHub Actions

Tests run automatically on:

- Every push
- Every pull request
- Scheduled daily runs

### Local CI Simulation

```bash
# Run tests as they would run in CI
npm run test:e2e:ci
```

## 📝 Contributing

### Adding New Tests

1. Create test file in appropriate category
2. Follow naming convention: `##-feature-name.cy.js`
3. Add descriptive test cases
4. Update README with new coverage
5. Ensure tests pass locally
6. Submit pull request

### Test Review Checklist

- [ ] Tests are independent
- [ ] Descriptive test names
- [ ] Proper assertions
- [ ] Error cases covered
- [ ] Documentation updated
- [ ] All tests pass

## 🆘 Getting Help

- Check [Cypress Documentation](https://docs.cypress.io/)
- Review existing tests for examples
- Ask in project Telegram group
- Create GitHub issue for bugs

## 📚 Additional Resources

- [Cypress Best Practices](https://docs.cypress.io/guides/references/best-practices)
- [Testing Library](https://testing-library.com/)
- [WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Web Performance](https://web.dev/performance/)

---

**Happy Testing! 🎉**
