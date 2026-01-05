#!/usr/bin/env python3
"""
Regression test to ensure generate_site.py produces output
identical to the known-good docs/index.html from commit 692924a.

This test:
1. Runs generate_site.py to regenerate docs/index.html
2. Compares the output to the known-good version
3. Reports any differences

Run with: python test_generate_site_regression.py
"""

import difflib
import os
import subprocess
import sys


def run_generate_site():
    """Run generate_site.py and return any errors."""
    script_path = 'control-plane/scripts/generate_site.py'
    
    if not os.path.exists(script_path):
        return False, f"Script not found: {script_path}"
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        if result.returncode != 0:
            return False, f"generate_site.py failed with exit code {result.returncode}:\n{result.stderr}"
        return True, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Timeout: generate_site.py took too long"
    except Exception as e:
        return False, f"Error running generate_site.py: {e}"


def load_file(path):
    """Load file content, return None if not exists."""
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        return f.read()


def compare_files(known_good_path, generated_path):
    """Compare two files and return differences."""
    known_good = load_file(known_good_path)
    generated = load_file(generated_path)
    
    if known_good is None:
        return None, f"Known-good file not found: {known_good_path}"
    
    if generated is None:
        return None, f"Generated file not found: {generated_path}"
    
    if known_good == generated:
        return True, "Files are identical! ✅"
    
    # Calculate differences
    known_lines = known_good.splitlines(keepends=True)
    generated_lines = generated.splitlines(keepends=True)
    
    diff = list(difflib.unified_diff(
        known_lines,
        generated_lines,
        fromfile='known_good_index.html',
        tofile='generated_index.html',
        lineterm=''
    ))
    
    # Count differences
    additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
    deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
    
    return False, {
        'additions': additions,
        'deletions': deletions,
        'diff_lines': len(diff),
        'known_good_lines': len(known_lines),
        'generated_lines': len(generated_lines),
        'diff': ''.join(diff[:100])  # First 100 lines of diff
    }


def test_generate_site_regression():
    """Main regression test."""
    print("=" * 60)
    print("generate_site.py Regression Test")
    print("=" * 60)
    print()
    
    known_good_path = 'tests/fixtures/known_good_index.html'
    generated_path = 'docs/index.html'
    
    # Step 1: Backup current generated file
    backup_path = generated_path + '.backup'
    if os.path.exists(generated_path):
        import shutil
        shutil.copy2(generated_path, backup_path)
        print(f"📦 Backed up current {generated_path} to {backup_path}")
    
    # Step 2: Run generate_site.py
    print("\n🔄 Running generate_site.py...")
    success, output = run_generate_site()
    
    if not success:
        print(f"❌ Failed to run generate_site.py: {output}")
        return False
    
    print(f"✅ generate_site.py completed")
    print(f"   Output preview: {output[:200]}...")
    
    # Step 3: Compare files
    print(f"\n📊 Comparing generated output to known-good version...")
    identical, result = compare_files(known_good_path, generated_path)
    
    if identical is None:
        print(f"❌ Error: {result}")
        return False
    
    if identical:
        print(f"\n✅ {result}")
        print("🎉 Regression test PASSED!")
        return True
    
    # Report differences
    print(f"\n❌ Files differ!")
    print(f"   Known-good lines: {result['known_good_lines']}")
    print(f"   Generated lines:  {result['generated_lines']}")
    print(f"   Additions:        +{result['additions']}")
    print(f"   Deletions:        -{result['deletions']}")
    print()
    print("First 100 lines of diff:")
    print("-" * 60)
    print(result['diff'])
    print("-" * 60)
    print()
    print("❌ Regression test FAILED!")
    print("   Fix generate_site.py until the output matches the known-good version.")
    
    return False


if __name__ == '__main__':
    success = test_generate_site_regression()
    sys.exit(0 if success else 1)
