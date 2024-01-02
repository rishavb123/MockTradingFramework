@echo off

echo mocks:
ls mocks -I __pycache__
echo.
echo.

echo research:
ls research -I __pycache__
echo.

for /D %%i in (research/*) do echo research/%%i: & (cd research/%%i & ls *.py) & (cd ../..)
