"""
Deprecated. Use before_after.py.

This script is kept only so that older commands do not fail silently.

Why it was replaced:
  * it carried five dead copies of the repository dictionary, left over from
    repeated in-place rewrites, and the live one still held the earlier
    97-repository keyword sample rather than the 199-repository random sample,
    so its output did not describe the sample the paper claims
  * it reported uncorrected p-values across hundreds of tests
  * it measured complexity on ".py" files only, in a Kotlin/Java corpus
  * it counted only "//" lines as comments, missing every Javadoc and KDoc

before_after.py reads the repository list from sampled_repos.json, so the
script and the sampling record can no longer disagree.
"""

import sys

sys.exit(
    "before_after_table.py is deprecated and produced results that did not "
    "match sampled_repos.json.\nRun: python3 before_after.py"
)
