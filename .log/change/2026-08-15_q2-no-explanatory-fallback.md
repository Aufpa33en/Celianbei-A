# Q2 no-explanatory fallback

- Removed the fallback that marked `constant_mean` as an explanatory model when no candidate qualified.
- Added an explicit no-eligible status and a fail-closed fit guard.
- Added a synthetic regression case that forces all explanatory candidates below baseline.
