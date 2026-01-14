#!/usr/bin/env python3
"""
ReDoS (Regular Expression Denial of Service) Vulnerability Checker

This script analyzes all regex patterns in the pattern-engine project
for potential ReDoS vulnerabilities.
"""

import re
import yaml
from pathlib import Path
from typing import List, Dict, Tuple


class ReDoSChecker:
    """Analyzes regex patterns for ReDoS vulnerabilities."""

    # Common ReDoS vulnerability patterns
    REDOS_PATTERNS = [
        # Nested quantifiers - catastrophic backtracking
        (r'\([^)]*[*+]\)[*+?]', 'Nested quantifiers (e.g., (a+)+, (a*)*, (a+)*)'),
        (r'\([^)]*[*+]\)\{', 'Nested quantifiers with counted repetition (e.g., (a+){2,})'),

        # Overlapping alternation with quantifiers
        (r'\([^)]*\|[^)]*\)[*+]', 'Alternation with quantifier (potential overlap)'),

        # Character class followed by itself with quantifiers
        (r'\[[^\]]+\][*+]\[[^\]]+\][*+]', 'Adjacent character classes with quantifiers'),

        # Greedy quantifiers followed by optional
        (r'[*+]\?', 'Greedy quantifier followed by optional (potential backtracking)'),

        # Multiple consecutive .* or .+
        (r'\.\*\.\*|\.\+\.\+', 'Multiple consecutive .* or .+ (excessive backtracking)'),

        # Word boundary with quantifiers that can cause issues
        (r'\\w[*+]\\w[*+]', 'Multiple \\w+ patterns (potential backtracking)'),
    ]

    def __init__(self, base_path: str = 'regex'):
        self.base_path = Path(base_path)
        self.vulnerabilities = []

    def check_pattern(self, pattern: str, pattern_id: str, file_path: str) -> List[Dict]:
        """Check a single regex pattern for ReDoS vulnerabilities."""
        issues = []

        # Check against known ReDoS patterns
        for redos_pattern, description in self.REDOS_PATTERNS:
            if re.search(redos_pattern, pattern):
                issues.append({
                    'pattern_id': pattern_id,
                    'file': str(file_path),
                    'pattern': pattern,
                    'issue': description,
                    'severity': 'HIGH'
                })

        # Additional heuristic checks
        issues.extend(self._check_complexity(pattern, pattern_id, file_path))

        return issues

    def _check_complexity(self, pattern: str, pattern_id: str, file_path: str) -> List[Dict]:
        """Check for complexity-based ReDoS risks."""
        issues = []

        # Check for multiple overlapping quantifiers
        quantifier_count = len(re.findall(r'[*+?]\??|\{\d+,?\d*\}', pattern))
        if quantifier_count > 5:
            issues.append({
                'pattern_id': pattern_id,
                'file': str(file_path),
                'pattern': pattern,
                'issue': f'High quantifier count ({quantifier_count}) - potential complexity risk',
                'severity': 'MEDIUM'
            })

        # Check for nested groups with quantifiers
        nested_groups = re.findall(r'\([^()]*\([^()]*\)[^()]*\)', pattern)
        for group in nested_groups:
            if re.search(r'[*+?]', group):
                issues.append({
                    'pattern_id': pattern_id,
                    'file': str(file_path),
                    'pattern': pattern,
                    'issue': f'Nested groups with quantifiers: {group}',
                    'severity': 'MEDIUM'
                })

        # Check for patterns like (a|ab)+ or (a|a?)+ which can cause exponential time
        alt_patterns = re.findall(r'\([^)]+\|[^)]+\)[*+]', pattern)
        for alt in alt_patterns:
            # Simple heuristic: check if alternatives might overlap
            if '|' in alt and ('+' in alt or '*' in alt):
                issues.append({
                    'pattern_id': pattern_id,
                    'file': str(file_path),
                    'pattern': pattern,
                    'issue': f'Alternation with quantifier (check for overlap): {alt}',
                    'severity': 'MEDIUM'
                })

        return issues

    def analyze_file(self, yaml_file: Path) -> List[Dict]:
        """Analyze all patterns in a YAML file."""
        issues = []

        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data or 'patterns' not in data:
                return issues

            for pattern_data in data['patterns']:
                pattern = pattern_data.get('pattern', '')
                pattern_id = pattern_data.get('id', 'unknown')

                issues.extend(self.check_pattern(pattern, pattern_id, yaml_file))

        except Exception as e:
            print(f"Error analyzing {yaml_file}: {e}")

        return issues

    def analyze_all(self) -> Tuple[List[Dict], int]:
        """Analyze all YAML files in the regex directory."""
        all_issues = []
        total_patterns = 0

        # Find all YAML files
        yaml_files = list(self.base_path.rglob('*.yml'))

        for yaml_file in yaml_files:
            issues = self.analyze_file(yaml_file)
            all_issues.extend(issues)

            # Count patterns
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and 'patterns' in data:
                        total_patterns += len(data['patterns'])
            except:
                pass

        return all_issues, total_patterns

    def generate_report(self):
        """Generate a comprehensive ReDoS vulnerability report."""
        print("=" * 80)
        print("ReDoS VULNERABILITY ANALYSIS REPORT")
        print("=" * 80)
        print()

        issues, total_patterns = self.analyze_all()

        print(f"Total patterns analyzed: {total_patterns}")
        print(f"Total potential vulnerabilities found: {len(issues)}")
        print()

        if not issues:
            print("✓ No ReDoS vulnerabilities detected!")
            print()
            print("All patterns appear to be safe from catastrophic backtracking.")
            return

        # Group by severity
        high_severity = [i for i in issues if i['severity'] == 'HIGH']
        medium_severity = [i for i in issues if i['severity'] == 'MEDIUM']

        print(f"HIGH severity issues: {len(high_severity)}")
        print(f"MEDIUM severity issues: {len(medium_severity)}")
        print()

        # Report HIGH severity issues
        if high_severity:
            print("=" * 80)
            print("HIGH SEVERITY ISSUES (Likely ReDoS Vulnerable)")
            print("=" * 80)
            print()

            for idx, issue in enumerate(high_severity, 1):
                print(f"{idx}. Pattern ID: {issue['pattern_id']}")
                print(f"   File: {issue['file']}")
                print(f"   Pattern: {issue['pattern']}")
                print(f"   Issue: {issue['issue']}")
                print()

        # Report MEDIUM severity issues
        if medium_severity:
            print("=" * 80)
            print("MEDIUM SEVERITY ISSUES (Potential ReDoS Risk)")
            print("=" * 80)
            print()

            for idx, issue in enumerate(medium_severity, 1):
                print(f"{idx}. Pattern ID: {issue['pattern_id']}")
                print(f"   File: {issue['file']}")
                print(f"   Pattern: {issue['pattern']}")
                print(f"   Issue: {issue['issue']}")
                print()

        # Recommendations
        print("=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print()
        print("For patterns with ReDoS vulnerabilities:")
        print("1. Replace nested quantifiers (e.g., (a+)+ -> a+)")
        print("2. Use atomic groups or possessive quantifiers where supported")
        print("3. Simplify alternations to avoid overlap")
        print("4. Consider using more specific character classes instead of .*")
        print("5. Add anchors (^, $, \\b) to limit backtracking scope")
        print("6. Test patterns with long, crafted inputs to verify performance")
        print()


if __name__ == '__main__':
    checker = ReDoSChecker()
    checker.generate_report()
