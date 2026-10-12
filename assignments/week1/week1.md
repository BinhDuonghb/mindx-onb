# TDD (Test-Driven Development)

TDD is a development approach that defines the expected behavior through tests before writing the implementation. The process follows the **Red-Green-Refactor** cycle.

**Red-Green-Refactor** can be understood as the three steps of implementing TDD:

- **RED:** Write a test case that defines the expected behavior. The test should fail because the required implementation does not exist yet.
- **GREEN:** Implement the minimum code required to satisfy the test case and make it pass.
- **REFACTOR:** Clean up or improve the code structure without changing its behavior.

## Pros

- **Clear requirements:** Developers know what behavior the implementation is expected to produce by defining the input and expected output in the test first.
- **Reduced regression bugs:** When logic is added or changed, existing test cases can reveal whether the change has broken previously expected behavior.
- **Easier maintenance:** Tests provide documentation of the expected behavior and make future changes safer.

## Cons

- **Changing requirements can require test updates:** If the requirements or business rules change frequently, the related implementation and test cases may both need to be updated.
- **Tests can be incomplete:** TDD does not guarantee that every possible scenario is covered. Developers may still miss important edge cases or test cases.

---

# Testing Levels

## 1. Unit Test

### Definition

A test that checks a small piece of logic, such as a function or method, independently from other components.

### Example

```text
calculateTotal(price, quantity)

→ Test whether calculateTotal(100, 2) returns 200.
```

### Pros

- Fast to run.
- Easy to debug.
- Helps detect bugs early.
- Tests business logic independently.

### Cons

- Does not verify how different components work together.
- May require mocking dependencies.
- Passing unit tests does not guarantee that the whole system works correctly.

---

## 2. Integration Test

### Definition

A test that checks multiple components or services working together to make sure they cooperate correctly.

### Example

```text
API → Service → Database
```

For example, test a `POST /users` API to make sure:

1. The API receives the request.
2. The service processes the data.
3. The user is correctly saved to the database.
4. The API returns the expected response.

### Pros

- Verifies that components work correctly together.
- Can detect problems with databases, APIs, and external services.
- More realistic than unit tests.

### Cons

- Slower than unit tests.
- More difficult to set up.
- Debugging can be harder because multiple components are involved.
- May require a test database or external services.

---

## 3. End-to-End (E2E) Test

### Definition

A test that verifies a complete user workflow from start to finish.

### Example

```text
Login
  ↓
Search for a product
  ↓
Add product to cart
  ↓
Checkout
  ↓
Make payment
  ↓
Receive order confirmation
```

An E2E test checks whether the **whole workflow works correctly**, rather than testing individual functions or components.

### Pros

- Tests the system from the user's perspective.
- Verifies that the entire workflow works correctly.
- Can catch problems that unit and integration tests may miss.

### Cons

- Slowest type of test.
- More expensive to maintain.
- Can be fragile because many components are involved.
- Debugging failures can be difficult.

---

# CLI Testing

CLI testing is not only about running tests. It can also support the **TDD workflow**, especially the **Red → Green → Refactor** cycle.

## 1. Create a Test Scaffold

For example:

```bash
myapp test create unit UserService
myapp test create integration UserApi
myapp test create e2e Checkout
```

These commands could generate the corresponding test structure:

```text
tests/
└── MyApp.UnitTests/
    └── Users/
        └── UserServiceTests.cs
```

This helps developers quickly create tests with a consistent project structure.

---

## 2. Run Tests by Testing Level

The CLI can provide commands to run tests at different levels:

```bash
myapp test unit
myapp test integration
myapp test e2e
myapp test all
```

It can also run tests for a specific feature:

```bash
myapp test unit --feature users
```

or:

```bash
myapp test integration --feature orders
```

This is especially useful when working on a specific module or feature.

---

## 3. Run a Specific Test

Running a specific test is particularly important for TDD.

For example:

```bash
myapp test unit --test UserCannotRegisterWithDuplicateEmail
```

The TDD workflow is usually not:

```text
Write one test
    ↓
Run 5,000 tests
```

Instead, it can be:

```text
Write one test
    ↓
Run that specific test
    ↓
Implement or modify the code
    ↓
Run the test again
    ↓
Fix the implementation
    ↓
Refactor
    ↓
Run the relevant test suite
```

This makes the **Red → Green → Refactor** cycle faster and more focused, especially when working on a specific piece of functionality.

# AI-Assisted TDD Workflow

AI can support TDD by generating test scenarios, identifying edge cases, and creating test cases. However, the developer remains responsible for defining expected behavior, making business decisions, implementing the solution, and validating the final result.

## Example: Authentication API

### Register

```text
POST /api/auth/register

Input:
- email
- password

Rules:
- Email is required
- Email must have a valid format
- Password must be at least 8 characters
- Email must be unique

Expected:
- Valid input → 201 Created
- Duplicate email → 409 Conflict
- Invalid input → 400 Bad Request
```

### Login

```text
POST /api/auth/login

Rules:
- Valid email and password → access token
- Unknown email → 401 Unauthorized
- Incorrect password → 401 Unauthorized
```

## AI-Assisted TDD Process

### 1. Requirement Analysis

The developer provides the requirements to AI.

AI helps:

- Generate test scenarios.
- Identify edge cases.
- Detect unclear or missing requirements.

Example:

```text
AI:
Should email comparison be case-insensitive?

Developer:
Yes. "Test@gmail.com" and "test@gmail.com" should be treated as the same email.
```

AI helps identify **specification gaps**, but the developer makes the final decision.

### 2. Generate Tests

AI can generate unit, integration, and E2E tests based on the agreed requirements.

Example unit tests:

```text
Register_WithValidData_ShouldCreateUser
Register_WhenEmailAlreadyExists_ShouldFail
Login_WithCorrectCredentials_ShouldReturnToken
Login_WithWrongPassword_ShouldFail
```

### 3. RED

Run the relevant tests:

```bash
myapp test unit --feature auth
```

Expected result:

```text
Passed: 0
Failed: 4

RED
```

The tests fail because the required implementation does not exist or does not satisfy the expected behavior.

### 4. GREEN

The developer implements the minimum required logic and runs the tests again.

```text
Passed: 4
Failed: 0

GREEN
```

The goal is to make the tests pass without adding unnecessary complexity.

### 5. Test Gap Analysis

After reaching GREEN, AI can review the current tests and suggest missing scenarios:

```text
Potential test gaps:

- Email whitespace
- Case-insensitive email comparison
- Password exactly 8 characters
- Concurrent duplicate registration
- Disabled account
```

The developer decides which scenarios are relevant to the actual requirements.

### 6. Integration and E2E Testing

After unit tests pass, higher-level tests can verify the complete system.

```text
Integration:

HTTP Request
    ↓
Controller
    ↓
Service
    ↓
Repository
    ↓
Test Database
```

```text
E2E:

Register
    ↓
Login
    ↓
Dashboard
```

This helps verify that individual components work together and that the complete user workflow works correctly.

## Overall Workflow

```text
Requirement
    ↓
AI Scenario Analysis
    ↓
Human confirms expected behavior
    ↓
AI generates tests
    ↓
RED
    ↓
Developer implements
    ↓
GREEN
    ↓
AI Test Gap Analysis
    ↓
Add relevant tests
    ↓
Refactor
    ↓
Regression Tests
    ↓
Integration Tests
    ↓
E2E Tests
```

## Responsibility Model

### AI

```text
- Scenario generation
- Edge-case discovery
- Test generation
- Test-gap analysis
```

### Developer

```text
- Define expected behavior
- Make business decisions
- Implement the solution
- Review AI-generated code and tests
- Validate results
- Approve refactoring
```

# How Testing Helps Control AI-Generated Implementation

AI can write implementation code, but the code should only be considered complete when it passes the **approved tests** that define the expected behavior.

## Example

For a login feature, the approved tests define:

```text
Correct credentials → Access token
Unknown email       → 401
Wrong password      → 401
Disabled account    → 403
```

AI implements `Login()` and the CLI runs:

```bash
myapp test unit --feature auth
```

If all tests pass:

```text
✓ Correct credentials
✓ Unknown email
✓ Wrong password
✓ Disabled account
```

the implementation satisfies the expected **behavior contract**.

If AI incorrectly returns `401` for a disabled account:

```text
Expected: 403
Actual:   401

FAIL
```

The implementation must be corrected.

## How Tests Control AI

### 1. Behavior Control

AI can choose different implementation details, but the output must match the approved behavior.

```text
Input → AI-generated implementation → Test → Expected behavior
```

### 2. Regression Control

When AI changes existing code, regression tests detect whether previous behavior was broken.

```text
Login tests    ✓
Register tests ✗
```

The change should not be accepted.

### 3. Scope Control

Tests can be combined with diff or file-change checks to detect unexpected modifications.

```text
Expected: AuthService.cs
Actual:   20 unrelated files changed
→ Reject / Review
```

### 4. Quality Control

Passing functional tests is not always enough. Additional gates can include:

```text
Tests
+ Static analysis
+ Lint / Type check
+ Security checks
+ Human review
```

## Important Guardrail

**AI should not modify approved tests just to make them pass.**

```text
Approved tests → Read-only
Production code → AI can modify
```

If a test needs to change, human approval should be required.

# Common Testing Mistakes

## 1. Over-testing

Writing too many tests that do not provide additional value.

For example, instead of testing every password length:

```text
7 characters  → invalid
8 characters  → valid
9 characters  → valid
10 characters → valid
...
```

Focus on important **boundary cases**:

```text
7 characters → invalid
8 characters → valid
```

> TDD does not mean "more tests are always better." The goal is to have enough tests to protect valuable behavior.

---

## 2. Weak Assertions

A weak assertion means the test exists, but the verification is not strong enough to prove that the expected behavior is correct.

Weak:

```csharp
var result = await service.Register(request);

Assert.NotNull(result);
```

This could pass even if the implementation is incorrect.

Stronger:

```csharp
Assert.True(result.Success);
Assert.Equal("test@gmail.com", result.Email);
Assert.NotNull(result.User);
```

The difference is:

```text
Missing test case
→ A scenario was not tested.

Weak assertion
→ The scenario was tested, but the result was not verified strongly enough.
```

---

## 3. Testing Implementation Details

Tests should focus on **what the system does**, rather than **how the code is implemented**.

For example, avoid tests that require a specific internal method to be called:

```csharp
passwordHasher.Verify(...);
```

Instead, test the observable behavior:

```text
Valid password → Login succeeds
Invalid password → Login fails
```

This allows the implementation to be refactored without unnecessarily breaking the tests.

> **Test behavior, not implementation details.**

---

## 4. Blindly Trusting AI Output

AI-generated tests and code can contain incorrect assumptions, missing scenarios, or weak assertions.

For example, the requirement says:

```text
Duplicate email → 409 Conflict
```

but AI generates:

```text
Duplicate email → 400 Bad Request
```

The test may still pass if the implementation follows the AI-generated test.

Therefore:

```text
Requirement
    ↓
AI proposes tests/code
    ↓
Human review
    ↓
Approved tests
    ↓
Implementation
    ↓
Validation
```

AI should assist the development process, but the developer remains responsible for validating the requirements, tests, and implementation.

Evidence Log: https://chatgpt.com/share/6ac74c34-812c-83ec-a670-fbc332a4a88b
