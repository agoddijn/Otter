# System Dependencies

## Required Dependencies

The CLI IDE requires the following system dependencies to be installed:

### 1. Neovim (>= 0.9.0)

**Purpose**: Core editor instance for LSP and TreeSitter integration

**Install**:
```bash
brew install neovim
```

**Verify**:
```bash
nvim --version
```

### 2. Ripgrep (rg)

**Purpose**: Fast workspace-wide search for "imported_by" analysis and file searching

**Install**:
```bash
brew install ripgrep
```

**Verify**:
```bash
rg --version
```

### 3. Node.js (>= 16.0.0)

**Purpose**: Runtime for LSP servers (pyright, typescript-language-server, etc.)

**Install**:
```bash
brew install node
```

**Verify**:
```bash
node --version
npm --version
```

### 4. Git

**Purpose**: Required by lazy.nvim plugin manager

**Install**:
```bash
brew install git
```

**Verify**:
```bash
git --version
```

### 5. C Compiler (gcc or clang)

**Purpose**: Compiling TreeSitter parsers

**Install**:
```bash
xcode-select --install
```

**Verify**:
```bash
gcc --version  # or clang --version
```

## Quick Setup (macOS)

### Check Dependencies

```bash
make check-deps
```

This will show which dependencies are installed and which are missing.

### Install All Dependencies

```bash
make install-deps
```

This will install all required dependencies via Homebrew.

### Manual Installation

If you prefer to install dependencies manually:

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install all dependencies
brew install neovim ripgrep node git

# Install Xcode Command Line Tools (for C compiler)
xcode-select --install
```

## Verification

After installation, verify all dependencies are available:

```bash
# Run the dependency checker
make check-deps

# Or use the standalone script
python3 scripts/check_deps.py
```

Expected output:
```
🔍 Checking system dependencies...

✅ Neovim: nvim (NVIM v0.11.4)
✅ Ripgrep: rg (ripgrep 14.1.0)
✅ Node.js: node (v24.2.0)
✅ Git: git (git version 2.48.1)
✅ C Compiler (gcc or clang): clang (Apple clang version 16.0.0)

✅ All required dependencies are installed!
```

## Runtime Dependency Checking

The MCP server automatically checks for required dependencies when it starts. If any are missing, you'll see a clear error message:

```
❌ Missing Required Dependencies

The following system dependencies are required but not installed:

  • Ripgrep (rg)
    Install: brew install ripgrep

Please install the missing dependencies and try again.

💡 Quick setup on macOS:
   make install-deps
```

## Troubleshooting

### Neovim Plugin Issues

If Neovim plugins fail to install:

```bash
# Manually install plugins
nvim --headless "+Lazy! sync" +qa

# Check TreeSitter parsers
nvim --headless "+TSInstallInfo" +qa
```

### TreeSitter Parser Compilation Failures

If TreeSitter parsers fail to compile:

1. Ensure you have a C compiler:
   ```bash
   xcode-select --install
   ```

2. Check for compilation errors in Neovim:
   ```bash
   nvim --headless "+checkhealth" +qa
   ```

3. Manually install specific parsers:
   ```bash
   nvim --headless "+TSInstall python javascript typescript" +qa
   ```

### Ripgrep Not Found

If you see "command not found: rg" errors:

1. Install ripgrep:
   ```bash
   brew install ripgrep
   ```

2. Verify it's in your PATH:
   ```bash
   which rg
   ```

3. Restart your terminal/shell

### Node.js LSP Servers

Install LSP servers for the languages you need:

```bash
# Python
npm install -g pyright

# TypeScript/JavaScript
npm install -g typescript-language-server typescript

# Rust
rustup component add rust-analyzer

# Go
go install golang.org/x/tools/gopls@latest
```

## CI/CD Environments

For Docker or CI environments, see the example Dockerfile:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    neovim \
    ripgrep \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y nodejs

# Install LSP servers
RUN npm install -g pyright typescript-language-server

# ... rest of your Dockerfile
```
