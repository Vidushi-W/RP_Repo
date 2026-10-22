@echo off
if not defined FLUTTER_ROOT exit /b 1
"%FLUTTER_ROOT%\bin\cache\dart-sdk\bin\dart.exe" --packages="%FLUTTER_ROOT%\packages\flutter_tools\.dart_tool\package_config.json" "%FLUTTER_ROOT%\bin\cache\flutter_tools.snapshot" %*

