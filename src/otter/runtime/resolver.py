"""Generic runtime resolver for all languages."""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback

from .specs import get_runtime_spec, RuntimeSpec, AutoDetectStrategy
from .types import RuntimeInfo


class RuntimeResolver:
    """Generic resolver for language runtimes.
    
    Works for any language defined in RUNTIME_SPECS.
    Uses declarative specifications instead of language-specific code.
    """
    
    def __init__(self, project_path: Path):
        """Initialize resolver.
        
        Args:
            project_path: Root path of the project
        """
        self.project_path = Path(project_path)
    
    def resolve_runtime(
        self,
        language: str,
        config: Optional[Any] = None,  # OtterConfig
    ) -> RuntimeInfo:
        """Resolve runtime for a language.
        
        Priority:
        1. Explicit config from .otter.toml
        2. Auto-detection using language-specific rules
        3. System runtime
        
        Args:
            language: Language name (e.g., "python", "javascript")
            config: Optional OtterConfig with explicit paths
            
        Returns:
            RuntimeInfo with resolved runtime details
            
        Raises:
            RuntimeError: If runtime cannot be found
        """
        spec = get_runtime_spec(language)
        
        # 1. Check explicit config (highest priority)
        if config:
            runtime = self._check_explicit_config(language, spec, config)
            if runtime:
                return runtime
        
        # 2. Auto-detect using spec rules
        runtime = self._auto_detect(language, spec)
        if runtime:
            return runtime
        
        # 3. System fallback
        runtime = self._system_fallback(language, spec)
        if runtime:
            return runtime
        
        # Not found
        display_name = spec.get("display_name", language)
        raise RuntimeError(
            f"{display_name} runtime not found.\n\n"
            f"Tried:\n"
            f"  1. Explicit config in .otter.toml\n"
            f"  2. Auto-detection in project\n"
            f"  3. System {spec['executable_name']}\n\n"
            f"Please install {display_name} or configure it in .otter.toml:\n"
            f"  [lsp.{language}]\n"
            f"  {spec['config_key']} = \"/path/to/{spec['executable_name']}\""
        )
    
    def _check_explicit_config(
        self,
        language: str,
        spec: Dict[str, Any],
        config: Any,
    ) -> Optional[RuntimeInfo]:
        """Check explicit configuration."""
        # Get language-specific config
        lang_config = config.lsp.language_configs.get(language)
        if not lang_config:
            return None
        
        # Get configured path
        config_key = spec.config_key
        configured_path = getattr(lang_config, config_key, None)
        if not configured_path:
            return None
        
        # Resolve template variables
        resolved_path = config.resolve_path(configured_path)
        
        # Verify it exists
        if not Path(resolved_path).exists():
            return None
        
        version = self._get_version(resolved_path, spec)
        
        return RuntimeInfo(
            language=language,
            path=resolved_path,
            source="explicit_config",
            version=version,
        )
    
    def _auto_detect(
        self,
        language: str,
        spec: RuntimeSpec,
    ) -> Optional[RuntimeInfo]:
        """Auto-detect runtime using spec rules."""
        auto_detect_rules = spec.auto_detect
        
        # Sort by priority (higher first)
        sorted_rules = sorted(
            auto_detect_rules,
            key=lambda r: r.priority,
            reverse=True
        )
        
        for rule in sorted_rules:
            detected = self._apply_detection_rule(language, rule, spec)
            if detected:
                return detected
        
        return None
    
    def _apply_detection_rule(
        self,
        language: str,
        rule: AutoDetectStrategy,
        spec: RuntimeSpec,
    ) -> Optional[RuntimeInfo]:
        """Apply a single detection rule."""
        rule_type = rule.type
        
        if rule_type == "venv":
            return self._detect_venv(language, rule, spec)
        elif rule_type == "conda":
            return self._detect_conda(language, rule, spec)
        elif rule_type == "nvm":
            return self._detect_nvm(language, rule, spec)
        elif rule_type == "local_node_modules":
            return self._detect_local_node_modules(language, rule, spec)
        elif rule_type == "toolchain_toml":
            return self._detect_toolchain_toml(language, rule, spec)
        elif rule_type == "toolchain_text":
            return self._detect_toolchain_text(language, rule, spec)
        elif rule_type == "go_mod":
            return self._detect_go_mod(language, rule, spec)
        
        return None
    
    def _detect_venv(
        self,
        language: str,
        rule: AutoDetectStrategy,
        spec: RuntimeSpec,
    ) -> Optional[RuntimeInfo]:
        """Detect Python virtual environment."""
        rule_type = rule.type
        
        for pattern in rule.patterns:
            venv_path = self.project_path / pattern
            if not venv_path.is_dir():
                continue
            
            # Try Unix path
            exe_path = venv_path / rule.executable_path
            if exe_path.exists():
                version = self._get_version(str(exe_path), spec)
                return RuntimeInfo(
                    language=language,
                    path=str(exe_path.resolve()),
                    source=f"auto_detect_{rule_type}",
                    version=version,
                )
            
            # Try Windows path
            if hasattr(rule, 'executable_path_win'):
                exe_path_win = venv_path / rule.executable_path_win
                if exe_path_win.exists():
                    version = self._get_version(str(exe_path_win), spec)
                    return RuntimeInfo(
                        language=language,
                        path=str(exe_path_win.resolve()),
                        source=f"auto_detect_{rule_type}",
                        version=version,
                    )
        
        return None
    
    def _detect_conda(
        self,
        language: str,
        rule: AutoDetectStrategy,
        spec: RuntimeSpec,
    ) -> Optional[RuntimeInfo]:
        """Detect conda environment."""
        # Similar to venv detection
        return self._detect_venv(language, rule, spec)
    
    def _detect_nvm(
        self,
        language: str,
        rule: AutoDetectStrategy,
        spec: RuntimeSpec,
    ) -> Optional[RuntimeInfo]:
        """Detect Node version from .nvmrc."""
        version_file = self.project_path / rule.version_file
        if not version_file.exists():
            return None
        
        # Read version
        version = version_file.read_text().strip()
        
        # Construct path from template
        path_template = rule.path_template
        path_str = path_template.replace("{version}", version)
        path = Path(path_str).expanduser()
        
        if not path.exists():
            return None
        
        node_version = self._get_version(str(path), spec)
        
        return RuntimeInfo(
            language=language,
            path=str(path.resolve()),
            source="auto_detect_nvm",
            version=node_version,
        )
    
    def _detect_local_node_modules(
        self,
        language: str,
        rule: AutoDetectStrategy,
        spec: RuntimeSpec,
    ) -> Optional[RuntimeInfo]:
        """Detect local node_modules installation."""
        for pattern in rule.patterns:
            local_path = self.project_path / pattern / rule.executable_path
            if local_path.exists():
                version = self._get_version(str(local_path), spec)
                return RuntimeInfo(
                    language=language,
                    path=str(local_path.resolve()),
                    source="auto_detect_local",
                    version=version,
                )
        
        return None
    
    def _detect_toolchain_toml(
        self,
        language: str,
        rule: AutoDetectStrategy,
        spec: RuntimeSpec,
    ) -> Optional[RuntimeInfo]:
        """Detect Rust toolchain from rust-toolchain.toml."""
        toolchain_file = self.project_path / rule.version_file
        if not toolchain_file.exists():
            return None
        
        try:
            with open(toolchain_file, "rb") as f:
                data = tomllib.load(f)
            
            # Navigate nested keys (e.g., "toolchain.channel")
            keys = rule.toml_key.split(".")
            value = data
            for key in keys:
                value = value.get(key)
                if value is None:
                    break
            
            if not value:
                value = rule.default
            
            # Rust uses rustup, not a direct path
            # Return toolchain name
            return RuntimeInfo(
                language=language,
                path=f"rustup::{value}",  # Special format
                source="auto_detect_toolchain",
                version=value,
            )
        
        except Exception:
            return None
    
    def _detect_toolchain_text(
        self,
        language: str,
        rule: AutoDetectStrategy,
        spec: RuntimeSpec,
    ) -> Optional[RuntimeInfo]:
        """Detect Rust toolchain from rust-toolchain file."""
        toolchain_file = self.project_path / rule.version_file
        if not toolchain_file.exists():
            return None
        
        toolchain = toolchain_file.read_text().strip()
        
        return RuntimeInfo(
            language=language,
            path=f"rustup::{toolchain}",
            source="auto_detect_toolchain",
            version=toolchain,
        )
    
    def _detect_go_mod(
        self,
        language: str,
        rule: AutoDetectStrategy,
        spec: RuntimeSpec,
    ) -> Optional[RuntimeInfo]:
        """Detect Go version from go.mod."""
        go_mod = self.project_path / rule.version_file
        if not go_mod.exists():
            return None
        
        content = go_mod.read_text()
        pattern = rule.parse
        match = re.search(pattern, content)
        
        if match:
            version = match.group(1)
            # Note: This just detects the version, still uses system go
            # Could extend to use specific Go version managers
            system_go = shutil.which("go")
            if system_go:
                return RuntimeInfo(
                    language=language,
                    path=system_go,
                    source="auto_detect_go_mod",
                    version=version,
                )
        
        return None
    
    def _system_fallback(
        self,
        language: str,
        spec: RuntimeSpec,
    ) -> Optional[RuntimeInfo]:
        """Try system commands as fallback."""
        system_commands = spec.system_commands
        
        for cmd in system_commands:
            path = shutil.which(cmd)
            if path:
                version = self._get_version(path, spec)
                return RuntimeInfo(
                    language=language,
                    path=path,
                    source="system",
                    version=version,
                )
        
        return None
    
    def _get_version(self, executable: str, spec: RuntimeSpec) -> Optional[str]:
        """Get version of an executable."""
        version_check = spec.version_check
        if not version_check:
            return None
        
        try:
            result = subprocess.run(
                [executable] + version_check.args,
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            output = result.stdout + result.stderr
            pattern = version_check.parse
            match = re.search(pattern, output)
            
            if match:
                return match.group(1)
        
        except Exception:
            pass
        
        return None

