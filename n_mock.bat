@echo off
for /l %%x in (1, 1, %2) do python -m mocks.%1.main