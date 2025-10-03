# Language Runtime Configuration - Unified Approach

## Problem

Different languages can have multiple runtime versions installed:
- **Python**: System Python vs venv vs conda
- **Node.js**: System Node vs nvm versions vs project-specific
- **Rust**: System Rust vs rustup toolchains
- **Go**: System Go vs multiple versions
- **Ruby**: System Ruby vs rbenv vs rvm

**LSP and DAP both need the same runtime!**

## Which Languages Need This?

### 🔴 **Critical (Must Have)**

#### **Python** ✅ (Already Implemented)
- **Why:** Virtual environments are standard
- **Problem:** LSP/DAP must use venv Python, not system
- **Solution:** Unified `python_path` config

#### **Node.js/TypeScript** 🚧 (Should Implement)
- **Why:** Projects often use specific Node versions (via nvm, .nvmrc)
- **Problem:** LSP (tsserver) and DAP need same Node
- **Example:** Project uses Node 18, but system has Node 20
- **Solution:** Add `node_path` config

### 🟡 **Important (Nice to Have)**

#### **Rust** 🟡
- **Why:** Different toolchains (stable, nightly, specific versions)
- **Problem:** rust-analyzer and debugging need same toolchain
- **Solution:** Add `rust_toolchain` config

#### **Go** 🟡
- **Why:** Projects might use specific Go versions
- **Problem:** gopls and delve need same Go
- **Solution:** Add `go_path` config

### 🟢 **Low Priority**

#### **Ruby, PHP, Java, etc.** 🟢
- Less common in modern development
- Can add on demand

## Proposed Unified Configuration

### .otter.toml Structure

```toml
# =============================================================================
# Language Runtime Configuration
# =============================================================================
# LSP and DAP will use these SAME runtime paths

[lsp.python]
enabled = true
server = "pyright"
python_path = "${VENV}/bin/python"  # Used by LSP AND DAP

[lsp.javascript]
enabled = true
server = "tsserver"
node_path = "${NVM}/versions/node/v18.17.0/bin/node"  # Used by LSP AND DAP

[lsp.typescript]
enabled = true
server = "tsserver"
node_path = "${NVM}/versions/node/v18.17.0/bin/node"  # Shared with JS

[lsp.rust]
enabled = true
server = "rust_analyzer"
rust_toolchain = "stable"  # or "nightly", "1.70.0"

[lsp.go]
enabled = true
server = "gopls"
go_path = "/usr/local/go/bin/go"  # or specific version
```

### Template Variables

```toml
# Otter should support these auto-detection variables:

${VENV}        # Auto-detect .venv/, venv/, env/
${NVM}         # Auto-detect ~/.nvm/
${NODE}        # Auto-detect Node from .nvmrc or PATH
${CARGO_HOME}  # Auto-detect ~/.cargo/
${GOPATH}      # Auto-detect from env or ~/go/
```

## Implementation Plan

### Phase 1: Node.js (High Priority) 🚧

**Why First:**
- Second most common after Python
- Projects often have specific Node versions
- `.nvmrc` is standard

**Changes Needed:**

```python
# config/parser.py
@dataclass
class LSPLanguageConfig:
    enabled: bool = True
    server: Optional[str] = None
    python_path: Optional[str] = None  # Python
    node_path: Optional[str] = None    # ✅ Already exists!
    settings: Dict[str, Any] = field(default_factory=dict)

# Extend to DAPLanguageConfig too
@dataclass
class DAPLanguageConfig:
    enabled: bool = True
    adapter: Optional[str] = None
    python_path: Optional[str] = None
    node_path: Optional[str] = None    # ✅ Add this
    configurations: List[Dict[str, Any]] = field(default_factory=list)
```

**Auto-detection for Node:**

```python
def _detect_node_path(self) -> str:
    """Detect Node.js path, preferring project-specific versions."""
    # 1. Check .nvmrc in project
    nvmrc = self.project_path / ".nvmrc"
    if nvmrc.exists():
        version = nvmrc.read_text().strip()
        nvm_node = Path.home() / ".nvm" / "versions" / "node" / f"v{version}" / "bin" / "node"
        if nvm_node.exists():
            return str(nvm_node)
    
    # 2. Check for local node_modules/.bin/node
    local_node = self.project_path / "node_modules" / ".bin" / "node"
    if local_node.exists():
        return str(local_node)
    
    # 3. System Node
    import shutil
    system_node = shutil.which("node")
    if system_node:
        return system_node
    
    raise RuntimeError("Node.js not found")
```

**Update DebugService:**

```python
def _get_node_path(self) -> str:
    """Get Node.js path using UNIFIED config (same as LSP)."""
    # 1. Check explicit config
    if self.config:
        js_config = self.config.lsp.language_configs.get("javascript")
        if js_config and js_config.node_path:
            return self.config.resolve_path(js_config.node_path)
    
    # 2. Auto-detect (same logic as above)
    return self._detect_node_path()
```

### Phase 2: Rust (Medium Priority) 🟡

**Changes Needed:**

```python
@dataclass
class LSPLanguageConfig:
    # ... existing ...
    rust_toolchain: Optional[str] = None  # "stable", "nightly", "1.70.0"

def _get_rust_toolchain(self) -> str:
    """Get Rust toolchain (same for LSP and DAP)."""
    # 1. Check explicit config
    if self.config:
        rust_config = self.config.lsp.language_configs.get("rust")
        if rust_config and rust_config.rust_toolchain:
            return rust_config.rust_toolchain
    
    # 2. Check rust-toolchain.toml
    toolchain_file = self.project_path / "rust-toolchain.toml"
    if toolchain_file.exists():
        # Parse and return channel
        pass
    
    # 3. Default to stable
    return "stable"
```

### Phase 3: Go (Medium Priority) 🟡

**Similar pattern:**

```python
@dataclass
class LSPLanguageConfig:
    # ... existing ...
    go_path: Optional[str] = None

def _get_go_path(self) -> str:
    """Get Go path (same for gopls and delve)."""
    # 1. Explicit config
    # 2. go.mod version hint
    # 3. System go
```

## Configuration Examples

### Multi-Language Project

```toml
# .otter.toml for a full-stack project

[lsp.python]
python_path = "${VENV}/bin/python"

[lsp.javascript]
node_path = "${NVM}/versions/node/v18.17.0/bin/node"

[lsp.typescript]
node_path = "${NVM}/versions/node/v18.17.0/bin/node"  # Same Node

[lsp.rust]
rust_toolchain = "stable"

[lsp.go]
go_path = "/usr/local/go/bin/go"
```

### Explicit Paths (CI/Production)

```toml
# Explicit paths for reproducibility

[lsp.python]
python_path = "/opt/python/3.11/bin/python"

[lsp.javascript]
node_path = "/opt/node/18.17.0/bin/node"
```

### Auto-Detection (Development)

```toml
# Just enable languages, let Otter auto-detect runtimes

[lsp.python]
enabled = true
# Will auto-detect .venv/bin/python

[lsp.javascript]
enabled = true
# Will auto-detect from .nvmrc or system Node
```

## Benefits

### 1. **Consistency** ✅
LSP and DAP use same runtime for each language

### 2. **Transparency** ✅
Explicit logging shows which runtime is used:
```
🐍 Using Python: /project/.venv/bin/python (same as LSP)
📦 Using Node.js: ~/.nvm/versions/node/v18.17.0/bin/node (same as LSP)
🦀 Using Rust: stable toolchain (same as LSP)
```

### 3. **Configurability** ✅
Override auto-detection when needed

### 4. **Auto-Detection** ✅
Works out of box for standard setups:
- Python: venv detection
- Node: .nvmrc support
- Rust: rust-toolchain.toml
- Go: go.mod

## Implementation Priority

### Immediate (This PR) ✅
- [x] Python unified config

### Next (High Priority) 🚧
- [ ] Node.js unified config
  - [ ] Add `node_path` to DAPLanguageConfig
  - [ ] Implement `_get_node_path()` in DebugService
  - [ ] Add .nvmrc detection
  - [ ] Explicit logging
  - [ ] Tests

### Later (Medium Priority) 🟡
- [ ] Rust toolchain config
- [ ] Go version config

### Future (Low Priority) 🟢
- [ ] Ruby (rbenv/rvm)
- [ ] PHP (different PHP versions)
- [ ] Java (different JDK versions)

## Testing Strategy

### For Each Language

```python
async def test_lsp_and_dap_use_same_node(tmp_path):
    """Test that LSP and DAP use the same Node.js."""
    # Create .nvmrc
    nvmrc = tmp_path / ".nvmrc"
    nvmrc.write_text("18.17.0")
    
    # Create server
    server = CliIdeServer(project_path=str(tmp_path))
    
    # Get Node from debug service
    debug_node = server.debugging._get_node_path()
    
    # Should use same Node as would be configured for LSP
    assert "18.17.0" in debug_node or ".nvmrc" in debug_node
```

## Error Messages

### Clear, Actionable Errors

**Before:**
```
Error: No debug configuration available for filetype: javascript
```

**After:**
```
📦 Using Node.js: ~/.nvm/versions/node/v18.17.0/bin/node
   (This is the same Node.js used by LSP servers)
   ⚠️  WARNING: Node.js debug adapter may not be available
   Install with: npm install -g node-debug2
```

## Migration Path

### Step 1: Document Current Behavior
```toml
# Python already uses unified config
[lsp.python]
python_path = "${VENV}/bin/python"
```

### Step 2: Add Node.js Support
```toml
# Add node_path to DAPLanguageConfig
[lsp.javascript]
node_path = "${NVM}/versions/node/v18.17.0/bin/node"
```

### Step 3: Extend to Other Languages
```toml
[lsp.rust]
rust_toolchain = "stable"

[lsp.go]
go_path = "/usr/local/go/bin/go"
```

## Conclusion

**Yes, we should extend the unified runtime config to other languages!**

### Priority Order:
1. ✅ **Python** (Done)
2. 🚧 **Node.js** (High priority - should do next)
3. 🟡 **Rust** (Medium priority)
4. 🟡 **Go** (Medium priority)
5. 🟢 **Others** (On demand)

### Key Principles:
1. **Same config** for LSP and DAP
2. **Explicit logging** of runtime paths
3. **Auto-detection** with override
4. **Template variables** for common cases
5. **Clear errors** with exact install commands

This ensures Otter has consistent, transparent runtime management across all languages.

