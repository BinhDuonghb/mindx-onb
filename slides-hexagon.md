---
theme: default
colorSchema: light
background: "#ffffff"
title: Hexagonal Architecture
info: |
  Core concept, architecture diagram, data flow, pros/cons, and code examples
fonts:
  sans: "Exo"
  serif: "Exo"
  mono: "SF Mono, Monaco, Consolas"
class: text-center
drawings:
  persist: false
transition: none
mdc: true
favicon: "/favicon.svg"
---

# Hexagonal Architecture

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

Core concepts, architecture diagram, data flow, pros/cons, and code examples

---

## Core Concept

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**Isolate business logic from external systems**

<div class="grid grid-cols-2 gap-4 mt-8 text-left">

<div>

**The Problem**
- Business logic mixed with frameworks
- Hard to test
- Hard to change technologies
- Tight coupling

</div>

<div class="mt-0.5">

**The Solution**
- Pure domain logic at core
- Interfaces (Ports) define contracts
- Adapters translate to/from externals
- Technology-agnostic core

</div>

</div>

---

## Hexagonal Architecture Diagram
<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />
<div class="flex justify-center items-center h-full">
<img src="/images/hexagon.webp" alt="Hexagonal Architecture Diagram showing Business Model at center, surrounded by Services/Repositories, Ports layer, and Adapters" class="w-4/5 translate-y-[-16px] max-w-2xl" />
</div>

---

## Data Flow

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

<div class="grid grid-cols-2 gap-8 mt-8">

<div>

**Inward (Request)**
```
REST/Event/SOAP Client
    ↓
Interface Adapter
    ↓
Services
    ↓
Business Model
```

</div>

<div>

**Outward (Response)**
```
Business Model
    ↓
Repositories
    ↓
Data Sources
    ↓
Infrastructure Adapter
    ↓
External System
```

</div>

</div>

---

## Pros & Cons / When to Apply

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

<div class="grid grid-cols-2 gap-8 mt-8 text-left">

<div>

**Advantages**
- Testability
- Flexibility
- Maintainability

**Good Fit**
- Complex logic
- Multiple integrations
- Long-term projects

</div>

<div class="mt-0.5">

**Disadvantages**
- Complexity
- Overhead
- Learning curve

**Not Ideal**
- Simple CRUD
- Prototypes
- Small teams

</div>

</div>

---

## Code Structure Example

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

```
src/
├── domain/                    # Core (Business Model)
│   ├── entities/
│   ├── services/
│   └── validators/
│
├── ports/                     # Interfaces (Ports)
│   ├── inbound/              # Primary Ports
│   └── outbound/             # Secondary Ports
│
└── adapters/                  # Implementations
    ├── primary/              # Interface Adapters
    └── secondary/            # Infrastructure Adapters
```

---

## Code Example: Domain Logic

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

```typescript
// Business Model - Pure logic, no framework
export class BuildService {
  constructor(
    private fileSystem: FileSystemPort,  // Port interface
    private processRunner: ProcessRunnerPort
  ) {}
  
  async executeTasks(tasks: Task[]): Promise<BuildResult> {
    const sortedTasks = this.sortByDependencies(tasks);
    
    for (const task of sortedTasks) {
      const config = await this.fileSystem.readFile(task.configPath);
      const result = await this.processRunner.execute(task.command);
      if (!result.success) return { success: false, error: result.error };
    }
    
    return { success: true };
  }
}
```

**No framework dependencies!**

---

## Code Example: Ports & Adapters

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

```typescript
// Port (Interface)
export interface FileSystemPort {
  readFile(path: string): Promise<string>;
}

// Adapter (Implementation)
export class NodeFSAdapter implements FileSystemPort {
  async readFile(path: string): Promise<string> {
    return fs.readFile(path, 'utf-8');
  }
}
```

**Port defines contract, Adapter implements it**

---

## Testing: Mock Adapters

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

```typescript
// Test with mock adapters - no real I/O
const mockFileSystem: FileSystemPort = {
  readFile: jest.fn().mockResolvedValue('config'),
  writeFile: jest.fn()
};

const buildService = new BuildService(mockFileSystem, mockRunner);
const result = await buildService.executeTasks(tasks);

expect(result.success).toBe(true);
```

**Fast tests - no external dependencies**

---

# Thank You

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

Questions?
