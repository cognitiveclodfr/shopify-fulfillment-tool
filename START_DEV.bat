@echo off
echo ========================================
echo Shopify Tool - Development Mode
echo ========================================
echo.

REM Set development environment variable
set FULFILLMENT_SERVER_PATH=D:\Dev\fulfillment-server-mock

echo Environment: DEVELOPMENT
echo Server Path: %FULFILLMENT_SERVER_PATH%
echo.

REM Check if dev structure exists
if not exist "%FULFILLMENT_SERVER_PATH%\Clients" (
    echo Dev environment not found. Running setup...
    python scripts/setup_dev_env.py "%FULFILLMENT_SERVER_PATH%"
    echo.
)

REM Check if test data exists
if not exist "data\test_input\test_orders.csv" (
    echo Test data not found. Creating...
    python scripts/create_test_data.py
    echo.
)

echo ========================================
echo Starting Shopify Tool...
echo ========================================
echo.
python gui_main.py

pause
