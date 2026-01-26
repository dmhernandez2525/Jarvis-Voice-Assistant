#!/bin/bash
# Generate icns icon from SVG for JarvisApp
# Requires: ImageMagick (brew install imagemagick) or rsvg-convert (brew install librsvg)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SVG_FILE="$SCRIPT_DIR/JarvisIcon.svg"
ICONSET_DIR="$SCRIPT_DIR/JarvisIcon.iconset"
ICNS_FILE="$SCRIPT_DIR/JarvisIcon.icns"

# Create iconset directory
mkdir -p "$ICONSET_DIR"

# Generate different sizes using rsvg-convert (preferred) or ImageMagick
if command -v rsvg-convert &> /dev/null; then
    echo "Using rsvg-convert..."
    for size in 16 32 64 128 256 512 1024; do
        rsvg-convert -w $size -h $size "$SVG_FILE" -o "$ICONSET_DIR/icon_${size}x${size}.png"
        if [ $size -le 512 ]; then
            rsvg-convert -w $((size*2)) -h $((size*2)) "$SVG_FILE" -o "$ICONSET_DIR/icon_${size}x${size}@2x.png"
        fi
    done
elif command -v convert &> /dev/null; then
    echo "Using ImageMagick..."
    for size in 16 32 64 128 256 512 1024; do
        convert -background none -resize ${size}x${size} "$SVG_FILE" "$ICONSET_DIR/icon_${size}x${size}.png"
        if [ $size -le 512 ]; then
            convert -background none -resize $((size*2))x$((size*2)) "$SVG_FILE" "$ICONSET_DIR/icon_${size}x${size}@2x.png"
        fi
    done
else
    echo "Error: Neither rsvg-convert nor ImageMagick found."
    echo "Install with: brew install librsvg"
    echo "Or: brew install imagemagick"
    exit 1
fi

# Convert to icns
iconutil -c icns "$ICONSET_DIR" -o "$ICNS_FILE"

# Clean up
rm -rf "$ICONSET_DIR"

echo "Generated: $ICNS_FILE"
