"""
Source-level metrics used by the before/after analysis.

Two fixes relative to the earlier version of this pipeline:

1. Comment density previously counted only lines starting with "//" in
   Java/Kotlin, so every block comment and every KDoc/Javadoc header was
   invisible. Since Javadoc/KDoc is the dominant documentation style in this
   corpus, that systematically under-counted documentation and made the
   metric incomparable across languages. Block comments are now handled.

2. Cyclomatic complexity and function length were restricted to ".py" files
   because lizard hits a RecursionError on very large generated Kotlin files.
   The sample is 65 Kotlin / 61 Java / 14 Python repositories, so that
   restriction left those two metrics based on a small, unrepresentative
   slice. The restriction is replaced with an explicit size guard that skips
   the pathological generated files and keeps every other language.
"""

import sys

import lizard

# lizard parses token streams recursively; the default limit trips on long
# single-expression files before the size guard can be judged on merit.
sys.setrecursionlimit(20000)

# Extensions lizard supports that actually occur in this corpus.
CODE_EXTENSIONS = {
    ".py", ".kt", ".java", ".scala", ".js", ".ts", ".cs", ".cpp", ".cc", ".c", ".h", ".hpp",
}

# Languages whose comments follow the C family convention.
C_FAMILY = {".kt", ".java", ".scala", ".js", ".ts", ".cs", ".cpp", ".cc", ".c", ".h", ".hpp"}

# Files above these bounds are machine-generated resource tables (for example
# compose-multiplatform's Drawable*.kt / String*.kt). They are not hand-written
# code, they dominate any average they enter, and they are what makes lizard
# recurse without end. Skipping them is a documented exclusion, not a workaround.
MAX_LINES = 5000
MAX_CHARS = 400_000


def file_extension(filename):
    """Return the lowercase extension of a filename, including the dot."""
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[1].lower()


def is_generated_scale(source_code):
    """True when a file is too large to be hand-written source worth measuring."""
    return len(source_code) > MAX_CHARS or source_code.count("\n") > MAX_LINES


def comment_ratio(source_code, extension):
    """
    Share of non-blank lines that are comment lines.

    Python: '#' line comments plus module/class/function docstrings delimited
    by triple quotes. C-family: '//' line comments plus '/* ... */' blocks,
    which covers Javadoc and KDoc. String literals containing comment markers
    are not excluded; this is a lightweight lexical measure, and the same bias
    applies equally to the pre- and post-LLM periods being compared.
    """
    if not source_code:
        return None

    lines = source_code.split("\n")
    non_blank = [line.strip() for line in lines if line.strip()]
    if not non_blank:
        return None

    comments = 0

    if extension == ".py":
        in_docstring = False
        delimiter = None
        for line in non_blank:
            if in_docstring:
                comments += 1
                if delimiter in line:
                    in_docstring = False
                    delimiter = None
                continue
            if line.startswith("#"):
                comments += 1
                continue
            for quote in ('"""', "'''"):
                if line.startswith(quote):
                    comments += 1
                    # a docstring opened and closed on the same line
                    if not (len(line) > 3 and line.endswith(quote)):
                        in_docstring = True
                        delimiter = quote
                    break

    elif extension in C_FAMILY:
        in_block = False
        for line in non_blank:
            if in_block:
                comments += 1
                if "*/" in line:
                    in_block = False
                continue
            if line.startswith("//"):
                comments += 1
                continue
            if line.startswith("/*"):
                comments += 1
                if "*/" not in line:
                    in_block = True
                continue

    else:
        return None

    return comments / len(non_blank)


def complexity(source_code, filename):
    """
    Mean cyclomatic complexity and mean function length for one file.

    Returns (None, None) when the file is not analysable: unsupported
    extension, empty, generated at scale, or rejected by the parser.
    """
    if not source_code:
        return None, None

    extension = file_extension(filename)
    if extension not in CODE_EXTENSIONS:
        return None, None
    if is_generated_scale(source_code):
        return None, None

    try:
        analysis = lizard.analyze_file.analyze_source_code(filename, source_code)
    except (RecursionError, Exception):
        return None, None

    functions = analysis.function_list
    if not functions:
        return None, None

    mean_cc = sum(f.cyclomatic_complexity for f in functions) / len(functions)
    mean_length = sum(f.length for f in functions) / len(functions)
    return mean_cc, mean_length


if __name__ == "__main__":
    # Self-check: the old implementation reported 0.0 comment density for the
    # Kotlin sample below, because every comment line is a block comment.
    kotlin = """/**
 * Computes a sum.
 * @param a first value
 */
fun add(a: Int, b: Int): Int {
    // guard
    if (a > 0) return a + b
    return b
}
"""
    python = '''def add(a, b):
    """Return the sum of a and b."""
    # guard
    if a > 0:
        return a + b
    return b
'''
    print("Kotlin comment density:", round(comment_ratio(kotlin, ".kt"), 3))
    print("Kotlin complexity     :", complexity(kotlin, "Sample.kt"))
    print("Python comment density:", round(comment_ratio(python, ".py"), 3))
    print("Python complexity     :", complexity(python, "sample.py"))
