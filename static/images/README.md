# Images Directory

This directory contains images used throughout the ASPIR website.

## Current Images:

- **Elevate Tribe Bg Remover.png** - Main logo (used in navigation and footer)
- **female-teacher-reading-her-pupils.jpg** - Hero section image
- **little-boy-listening-his-teacher-through-headphones.jpg** - Available for use

## Usage:

All images are loaded using Django's static files system:
```django
{% load static %}
<img src="{% static 'images/filename.jpg' %}" alt="Description">
```

## Supported Formats:
- PNG (recommended for logos with transparency)
- JPG (recommended for photos)
- SVG (for scalable graphics)
