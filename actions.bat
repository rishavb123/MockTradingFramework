@echo off

echo mocks:
ls mocks -I __pycache__
echo.

ls -R research -I __pycache__ -I config.py