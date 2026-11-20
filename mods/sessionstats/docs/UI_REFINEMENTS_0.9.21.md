# Centered battle data and aligned finance columns in 0.9.21

Individual battle cards use a centered pair of data tables in the wide
720-logical-pixel preset. The performance table receives more width, and the
finance table has a bounded allocation instead of stretching across all
remaining card space. The data stays grouped around the card center without
expanding the currency-caption lane unnecessarily.
Numeric values are centered in their performance and financial columns.

Medium 500-logical-pixel battle cards assign financial columns from the known
logical card budget. Financial headings, base and received credit rows, the
shared Costs column and Bonds use the same column boundaries. The allocation
does not rely on a stale measurement of a flex table during resizing.

The change concerns individual battle cards. Vehicle, map and tier aggregates
retain their existing layout, including single-line captions, ellipsis and
full-caption custom help. Full figures and both credit rows remain available
in battle cards. Narrower layouts retain their readable fallback arrangement.

These notes describe the intended layout and do not claim live-client
verification or a completed validation result.
