# Binary File Declaration

This add-on contains no binary files.

All Python dependencies bundled into lib/ at build time are pure Python.
The grpcio and protobuf transitive dependencies (which contain compiled
code) are excluded from the package via lib/exclude.txt; the add-on does
not use the code paths that require them.
