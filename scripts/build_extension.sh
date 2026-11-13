#!/usr/bin/env bash
set -e

# Alpha Research Pilot - Extension Build Script
cd "$(dirname "$0")/../extension"

echo "Building Alpha Research Pilot extension..."
npm run build
echo "Build complete. Unpacked extension is available in extension/dist/"
