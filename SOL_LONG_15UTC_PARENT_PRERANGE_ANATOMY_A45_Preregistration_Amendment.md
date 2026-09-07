# A45 Preregistration Amendment — Adequate Development Block Definition

This amendment is committed **before A45 implementation and before any A45 outcome inspection**.

The original A45 preregistration uses the phrase `adequate Development block` but did not explicitly freeze its sample-size definition.

For A45, an adequate Development block is now frozen as:
- at least **20 stress WIN** rows; and
- at least **20 stress FAIL** rows
for the feature under evaluation after dropping only non-finite values for that feature.

The preregistered block-direction requirement therefore means:
- all six Development blocks are evaluated independently;
- only blocks meeting the 20 WIN / 20 FAIL minimum are adequate;
- at least 4 adequate blocks must have a non-zero median gap with the same sign as pooled Development.

No other A45 rule, feature, threshold, or verdict condition changes.
