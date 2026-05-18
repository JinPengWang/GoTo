GoTo Windows install
====================

For normal users:

1. Download the GoTo Windows release zip.
2. Extract the zip to a folder you keep, for example D:\Apps\GoTo.
3. Double-click install.bat.

Do not use the GitHub source-code zip for normal installation. The source
package does not include a freshly built GoTo.exe.

If GoTo stops working later, double-click repair.bat.

For developers:

1. Install Python 3.8+.
2. Run:
     python -m pip install -r requirements-build.txt
     build.bat
3. Then run install.bat.
