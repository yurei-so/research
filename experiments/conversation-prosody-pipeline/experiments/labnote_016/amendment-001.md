# Amendment 001: contour missing-bin handling

The first extractor execution exposed an implementation artifact before the result was
interpreted or recorded. Contour thirds were initially divided across the full WAV and
an empty voiced final third was encoded with an extreme numeric sentinel. That sentinel
could dominate standardized distances while representing only trailing silence.

The extractor now defines the previously underspecified contour span as the first voiced
frame through the last voiced frame, divides that span into thirds, computes energy from
all frames in each third, and uses the clip median F0 when a third has no pitch estimate.
The preregistered feature families, labels, distance statistic, permutation test, and
success threshold are unchanged. The initial output was overwritten and is not treated
as an experimental result.
