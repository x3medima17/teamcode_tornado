cd tmp
find * -maxdepth 0 -name 'file' -prune -o -exec rm -rf '{}' ';'
