# Generic Runtime Resolver - Better Architecture

## Problem with Language-Specific Approach

**What we almost did (BAD):**
```python
def _get_python_path(self) -> str:
    # Python-specific logic...

def _get_node_path(self) -> str:
    # Node-specific logic...

def _get_rust_toolchain(self) -> str:
    # Rust-specific logic...

# Need to write a new function for every language! ❌
```

**Problems:**
- ❌ Code duplication
- ❌ Hard to maintain
- ❌ Hard to add new languages
- ❌ Language-specific logic scattered everywhere

## The Better Way: Generic Runtime Resolver

### Single Generic Function

```python
class RuntimeResolver:
    """Generic runtime resolver for any language."""
    
    def resolve_runtime(
        self,
        language: str,
        config: OtterConfig,
        project_path: Path
    ) -> RuntimeInfo:
        """Resolve runtime for any language using declarative config."""
        
        # 1. Check explicit config
        explicit = self._check_explicit_config(language, config)
        if explicit:
            return explicit
        
        # 2. Auto-detect using language-specific rules
        detected = self._auto_detect(language, project_path)
        if detected:
            return detected
        
        # 3. System fallback
        return self._system_fallback(language)
```

### Declarative Runtime Specifications

Instead of code, use **data**:

```python
# runtime_specs.py - Configuration, not code!
RUNTIME_SPECS = {
    "python": {
        "executable_name": "python",
        "config_key": "python_path",
        "auto_detect": [
            {
                "type": "venv",
                "patterns": [".venv", "venv", "env", ".env"],
                "executable_path": "bin/python",  # Unix
                "executable_path_win": "Scripts/python.exe",  # Windows
            },
            {
                "type": "conda",
                "patterns": ["conda", ".conda"],
                "executable_path": "bin/python",
            },
        ],
        "system_command": "python3",
    },
    
    "javascript": {
        "executable_name": "node",
        "config_key": "node_path",
        "auto_detect": [
            {
                "type": "nvm",
                "version_file": ".nvmrc",  # Read version from here
                "path_template": "~/.nvm/versions/node/v{version}/bin/node",
            },
            {
                "type": "local",
                "patterns": ["node_modules/.bin"],
                "executable_path": "node",
            },
        ],
        "system_command": "node",
    },
    
    "rust": {
        "executable_name": "cargo",
        "config_key": "rust_toolchain",
        "auto_detect": [
            {
                "type": "toolchain_file",
                "version_file": "rust-toolchain.toml",
                "path_template": "rustup run {version} cargo",
            },
            {
                "type": "toolchain_file",
                "version_file": "rust-toolchain",
                "path_template": "rustup run {version} cargo",
            },
        ],
        "system_command": "cargo",
    },
    
    "go": {
        "executable_name": "go",
        "config_key": "go_path",
        "auto_detect": [
            {
                "type": "version_file",
                "version_file": "go.mod",
                "extract_pattern": r"go\s+(\d+\.\d+)",
            },
        ],
        "system_command": "go",
    },
}
```

### Generic Detection Logic

```python
class RuntimeResolver:
    def __init__(self, specs: Dict[str, Any]):
        self.specs = specs
    
    def resolve_runtime(
        self,
        language: str,
        config: OtterConfig,
        project_path: Path
    ) -> RuntimeInfo:
        """Generic resolution - works for ALL languages."""
        
        if language not in self.specs:
            raise ValueError(f"Unsupported language: {language}")
        
        spec = self.specs[language]
        
        # 1. Explicit config (highest priority)
        config_key = spec["config_key"]
        explicit_path = self._get_from_config(language, config_key, config)
        if explicit_path:
            return RuntimeInfo(
                language=language,
                path=explicit_path,
                source="explicit_config",
                version=self._get_version(explicit_path),
            )
        
        # 2. Auto-detect using spec rules
        for detection_rule in spec.get("auto_detect", []):
            detected = self._apply_detection_rule(
                detection_rule, project_path
            )
            if detected:
                return RuntimeInfo(
                    language=language,
                    path=detected,
                    source=f"auto_detect_{detection_rule['type']}",
                    version=self._get_version(detected),
                )
        
        # 3. System fallback
        system_cmd = spec["system_command"]
        system_path = shutil.which(system_cmd)
        if system_path:
            return RuntimeInfo(
                language=language,
                path=system_path,
                source="system",
                version=self._get_version(system_path),
            )
        
        raise RuntimeError(
            f"{language} runtime not found. "
            f"Install {system_cmd} or configure in .otter.toml"
        )
    
    def _apply_detection_rule(
        self, rule: Dict[str, Any], project_path: Path
    ) -> Optional[str]:
        """Apply a single detection rule generically."""
        
        if rule["type"] == "venv":
            # Check patterns for venv
            for pattern in rule["patterns"]:
                venv_path = project_path / pattern
                if venv_path.is_dir():
                    # Unix
                    exe_path = venv_path / rule["executable_path"]
                    if exe_path.exists():
                        return str(exe_path.resolve())
                    # Windows
                    if "executable_path_win" in rule:
                        exe_path_win = venv_path / rule["executable_path_win"]
                        if exe_path_win.exists():
                            return str(exe_path_win.resolve())
        
        elif rule["type"] == "nvm":
            # Read version from file, construct path
            version_file = project_path / rule["version_file"]
            if version_file.exists():
                version = version_file.read_text().strip()
                path_template = rule["path_template"]
                path = path_template.replace("{version}", version)
                path = Path(path).expanduser()
                if path.exists():
                    return str(path.resolve())
        
        elif rule["type"] == "toolchain_file":
            # Rust toolchain detection
            toolchain_file = project_path / rule["version_file"]
            if toolchain_file.exists():
                if toolchain_file.suffix == ".toml":
                    # Parse TOML
                    import tomllib
                    with open(toolchain_file, "rb") as f:
                        data = tomllib.load(f)
                    version = data.get("toolchain", {}).get("channel", "stable")
                else:
                    # Plain text
                    version = toolchain_file.read_text().strip()
                
                return rule["path_template"].replace("{version}", version)
        
        # Add more detection types as needed...
        
        return None
```

### Usage (Simple!)

```python
class DebugService:
    def __init__(self, nvim_client, project_path, config):
        self.nvim_client = nvim_client
        self.project_path = Path(project_path)
        self.config = config
        
        # Single generic resolver for ALL languages!
        from ..runtime import RuntimeResolver, RUNTIME_SPECS
        self.runtime_resolver = RuntimeResolver(RUNTIME_SPECS)
    
    async def start_debug_session(self, file, module, language, ...):
        # Generic resolution - same for all languages!
        runtime = self.runtime_resolver.resolve_runtime(
            language=language,
            config=self.config,
            project_path=self.project_path
        )
        
        # Explicit logging (generic!)
        print(f"\n🔧 Using {language} runtime: {runtime.path}")
        print(f"   Source: {runtime.source}")
        print(f"   Version: {runtime.version}")
        print(f"   (This is the same runtime used by LSP servers)")
        
        # Pass to DAP
        result = await self.nvim_client.dap_start_session(
            ...,
            runtime_path=runtime.path,  # Generic!
        )
```

## Benefits of Generic Approach

### 1. **Single Source of Truth** ✅

All runtime logic in one place: `RUNTIME_SPECS`

### 2. **Easy to Add Languages** ✅

```python
# Adding a new language is just adding data, not code!
RUNTIME_SPECS["ruby"] = {
    "executable_name": "ruby",
    "config_key": "ruby_path",
    "auto_detect": [
        {
            "type": "rbenv",
            "version_file": ".ruby-version",
            "path_template": "~/.rbenv/versions/{version}/bin/ruby",
        },
    ],
    "system_command": "ruby",
}
```

### 3. **No Code Duplication** ✅

One `resolve_runtime()` function works for all languages

### 4. **Testable** ✅

```python
def test_runtime_resolver():
    resolver = RuntimeResolver(RUNTIME_SPECS)
    
    # Test Python
    runtime = resolver.resolve_runtime("python", config, project_path)
    assert runtime.path.endswith("/.venv/bin/python")
    
    # Test Node
    runtime = resolver.resolve_runtime("javascript", config, project_path)
    assert "nvm" in runtime.path
    
    # Same test pattern for all languages!
```

### 5. **User-Extensible** ✅

Users can provide custom runtime specs in config:

```toml
# .otter.toml
[runtime.mycompiler]
executable_name = "mycompiler"
config_key = "mycompiler_path"
system_command = "mycompiler"

[runtime.mycompiler.auto_detect]
type = "venv"
patterns = [".mycompiler"]
executable_path = "bin/mycompiler"
```

## Configuration Examples

### Declarative (.otter.toml)

```toml
# Single pattern for all languages!

[lsp.python]
python_path = "${VENV}/bin/python"  # Auto-resolves to .venv/bin/python

[lsp.javascript]
node_path = "${NVM}/bin/node"  # Auto-resolves from .nvmrc

[lsp.rust]
rust_toolchain = "stable"  # Resolves to rustup run stable cargo
```

### Runtime Specifications (YAML Alternative)

Could even externalize specs to YAML:

```yaml
# runtime_specs.yaml
python:
  executable_name: python
  config_key: python_path
  auto_detect:
    - type: venv
      patterns: [.venv, venv, env]
      executable_path: bin/python
  system_command: python3

javascript:
  executable_name: node
  config_key: node_path
  auto_detect:
    - type: nvm
      version_file: .nvmrc
      path_template: ~/.nvm/versions/node/v{version}/bin/node
  system_command: node
```

## Implementation

### File Structure

```
src/otter/runtime/
├── __init__.py
├── resolver.py          # Generic RuntimeResolver class
├── specs.py             # RUNTIME_SPECS data
└── types.py             # RuntimeInfo dataclass
```

### Minimal Code

```python
# types.py
@dataclass
class RuntimeInfo:
    language: str
    path: str
    source: str  # "explicit_config", "auto_detect_venv", "system"
    version: Optional[str] = None

# resolver.py
class RuntimeResolver:
    def __init__(self, specs: Dict[str, Any]):
        self.specs = specs
    
    def resolve_runtime(self, language, config, project_path) -> RuntimeInfo:
        # Generic logic as shown above
        pass

# specs.py
RUNTIME_SPECS = {
    # Data, not code!
}
```

## Migration

### Phase 1: Create Generic Resolver

```python
# Keep existing _get_python_path() for backward compat
def _get_python_path(self) -> str:
    # Delegate to generic resolver
    runtime = self.runtime_resolver.resolve_runtime(
        "python", self.config, self.project_path
    )
    return runtime.path
```

### Phase 2: Use Generic Resolver Directly

```python
# Replace language-specific code
runtime = self.runtime_resolver.resolve_runtime(
    language, self.config, self.project_path
)
```

### Phase 3: Remove Language-Specific Functions

All language-specific functions replaced by generic resolver + specs.

## Comparison

### Before (Language-Specific)

```python
# 500+ lines of duplicated logic
def _get_python_path(self): ...     # 50 lines
def _get_node_path(self): ...       # 50 lines
def _get_rust_toolchain(self): ... # 50 lines
def _get_go_path(self): ...         # 50 lines
# ... need to add more for each language
```

### After (Generic)

```python
# ~200 lines of generic logic + data
class RuntimeResolver:  # 100 lines
    def resolve_runtime(self, language, ...):
        # Works for ALL languages!

RUNTIME_SPECS = {  # 100 lines of data
    "python": {...},
    "javascript": {...},
    "rust": {...},
    # Easy to add more!
}
```

## Conclusion

**Yes, there is a much better way!**

### Don't Do:
❌ Language-specific functions everywhere  
❌ Duplicated detection logic  
❌ Hard-coded paths  

### Do Instead:
✅ Single generic `RuntimeResolver`  
✅ Declarative `RUNTIME_SPECS`  
✅ Data-driven configuration  
✅ User-extensible specs  

This approach is:
- **Maintainable** - One place to update
- **Scalable** - Easy to add languages
- **Testable** - Generic test patterns
- **Flexible** - Users can extend
- **DRY** - No duplication

**We should refactor to this generic approach before adding more languages!**

