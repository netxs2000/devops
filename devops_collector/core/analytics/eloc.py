"""ELOC (Equivalent Lines of Code) Analysis Module

This module implements the Code Equivalent calculation algorithm defined in
docs/design/ELOC_METRIC_DESIGN.md. It provides methods to analyze code
changes and calculate weighted contribution scores.
"""
import re
import os
from typing import Dict, List, Optional
from pydantic import BaseModel

class ELOCOptions(BaseModel):
    """Configuration options for ELOC calculation."""
    ignore_generated: bool = True
    ignore_whitespace: bool = True
    test_file_pattern: str = r"(test_|spec_|tests/|__tests__/)"
    doc_file_pattern: str = r"\.(md|rst|txt|doc|docx)$"
    config_file_pattern: str = r"\.(json|yaml|yml|xml|html|css|scss|conf|ini|toml)$"
    generated_file_pattern: str = r"(lock|min\.js|bundle\.js|build/|dist/|vendor/)"

class ELOCResult(BaseModel):
    """Result of ELOC analysis for a single file or commit."""
    raw_additions: int = 0
    raw_deletions: int = 0
    eloc_score: float = 0.0
    comment_lines: int = 0
    test_lines: int = 0
    complexity_score: float = 0.0

class ELOCAnalyzer:
    """Core analyzer for calculating Code Equivalent scores."""
    
    def __init__(self, options: ELOCOptions = ELOCOptions()):
        self.options = options
        # Regex for identifying comments in various languages
        self.comment_patterns = {
            'python': {
                'line': r'^\s*#',
                'docstring_start': r'^\s*("""|\'\'\')',
                'docstring_end': r'("""|\'\'\')\s*$'
            },
            'c_style': { # Java, C++, C#, JS, Go
                'line': r'^\s*//',
                'block_start': r'^\s*/\*',
                'block_end': r'\*/\s*$'
            }
        }
        # Regex for "Why" comments (High Value)
        self.high_value_comment_re = re.compile(
            r"(TODO|FIXME|HACK|NOTE|WARNING|IMPORTANT|ISSUE|BUG|REF|SEE|WHY)", 
            re.IGNORECASE
        )
        # Regex for "Dead Code" (Commented out code)
        self.dead_code_re = re.compile(
            r"^\s*[#//].*(=|\{|\}|def |class |function |return |if |for |while |print\(|logger\.)",
            re.IGNORECASE
        )

    def analyze_commit_diff(self, file_path: str, diff_lines: List[str]) -> ELOCResult:
        """Analyzes a list of diff lines for a specific file.
        
        Args:
            file_path: Relative path of the file.
            diff_lines: List of changes lines (starting with + or -).
            
        Returns:
            ELOCResult: Calculated scores.
        """
        result = ELOCResult()
        
        # 0. File Level Filtering
        if self._is_generated(file_path):
            return result # Score 0 for generated files
            
        file_weight = self._get_file_weight(file_path)
        is_test_file = self._is_test_file(file_path)
        
        # Test code bonus
        if is_test_file:
            result.test_lines = len([l for l in diff_lines if l.startswith('+')])
        
        test_multiplier = 1.2 if is_test_file else 1.0

        for line in diff_lines:
            content = line[1:].rstrip() # Remove +/- marker
            
            # 1. Whitespace filter
            if self.options.ignore_whitespace and not content.strip():
                continue
                
            # 2. Determine Behavior Weight
            behavior_weight = 1.0
            if line.startswith('+'):
                result.raw_additions += 1
                behavior_weight = 1.0
            elif line.startswith('-'):
                result.raw_deletions += 1
                behavior_weight = 0.8 # Standard deletion
            else:
                continue # Context lines (if any)
                
            # 3. Content Analysis & Weighting
            line_weight = 1.0
            
            # Check if it's a comment
            if self._is_comment_line(file_path, content):
                result.comment_lines += 1
                
                if self._is_dead_code(content):
                    line_weight = 0.0 # Penalty for dead code
                elif self._is_high_value_comment(content):
                    line_weight = 1.2 # Bonus for explanation
                else:
                    line_weight = 0.8 # Standard docstring/comment
            
            # Calculate final score for this line
            # ELOC = Line * FileWeight * LineWeight * BehaviorWeight * TestBonus
            score = 1.0 * file_weight * line_weight * behavior_weight * test_multiplier
            result.eloc_score += score
            
        return result

    def _get_file_weight(self, file_path: str) -> float:
        """Determines weight based on file extension."""
        if re.search(self.options.config_file_pattern, file_path, re.IGNORECASE):
            return 0.1 # Config/Data files
        if re.search(self.options.doc_file_pattern, file_path, re.IGNORECASE):
            return 0.8 # Documentation
        return 1.0 # Core Logic

    def _is_generated(self, file_path: str) -> bool:
        return bool(re.search(self.options.generated_file_pattern, file_path, re.IGNORECASE))
        
    def _is_test_file(self, file_path: str) -> bool:
        return bool(re.search(self.options.test_file_pattern, file_path, re.IGNORECASE))

    def _is_comment_line(self, file_path: str, content: str) -> bool:
        """Simple heuristic to detect comment lines based on file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        patterns = self.comment_patterns.get('c_style') # Default to C-style
        
        if ext in ['.py', '.yaml', '.yml', '.sh', '.rb', '.pl']:
            patterns = self.comment_patterns['python']
            
        if not patterns: return False
        
        content = content.strip()
        return bool(re.match(patterns['line'], content))

    def _is_high_value_comment(self, content: str) -> bool:
        return bool(self.high_value_comment_re.search(content))

    def _is_dead_code(self, content: str) -> bool:
        return bool(self.dead_code_re.search(content))
