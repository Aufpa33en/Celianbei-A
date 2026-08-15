# Q2 manifest path portability

- Replaced platform-dependent `str(Path)` serialization with POSIX repository-relative paths.
- Added a Windows regression assertion rejecting backslashes in the manifest.
- Normalized the published manifest without changing model results.
