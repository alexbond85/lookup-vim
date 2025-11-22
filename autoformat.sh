#!/bin/bash

if ! command -v isort &> /dev/null
then
    echo "isort not found, refer to CONTRIBUTING.md to set up dev environment first."
    exit
fi

if ! command -v pyink &> /dev/null
then
    echo "pyink not found, refer to CONTRIBUTING.md to set up dev environment first."
    exit
fi

echo '---------------------------------------'
echo '|  Organizing imports for src/...'
echo '---------------------------------------'

isort src/
echo 'All done! ✨ 🍰 ✨'

echo '---------------------------------------'
echo '|  Organizing imports for tests/...'
echo '---------------------------------------'

isort tests/
echo 'All done! ✨ 🍰 ✨'

echo '---------------------------------------'
echo '|  Auto-formatting src/...'
echo '---------------------------------------'

find -L src/ -not -path "*/.*" -type f -name "*.py" -exec pyink --config pyproject.toml {} +

echo '---------------------------------------'
echo '|  Auto-formatting tests/...'
echo '---------------------------------------'

find -L tests/ -not -path "*/.*" -type f -name "*.py" -exec pyink --config pyproject.toml {} +

echo ''
echo '✨ All formatting complete! ✨'

