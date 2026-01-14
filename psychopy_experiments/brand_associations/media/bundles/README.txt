BUNDLE IMAGES FOLDER STRUCTURE
==============================

This folder should contain product images for the 45 bundles.
Each bundle has a FOCAL product (main product) and a TIE-IN product (complementary item).

FOLDER STRUCTURE
----------------
Place images in one of two formats:

OPTION 1: Nested folders (recommended)
    bundles/
        bundle_01/
            focal.jpg (or focal.png)
            tiein.jpg (or tiein.png)
        bundle_02/
            focal.jpg
            tiein.jpg
        ...
        bundle_45/
            focal.jpg
            tiein.jpg

OPTION 2: Flat structure
    bundles/
        bundle_01_focal.jpg
        bundle_01_tiein.jpg
        bundle_02_focal.jpg
        bundle_02_tiein.jpg
        ...
        bundle_45_focal.jpg
        bundle_45_tiein.jpg

SUPPORTED FORMATS
-----------------
- .jpg / .jpeg
- .png
- .bmp
- .gif

IMAGE REQUIREMENTS
------------------
- Rectangular images (no transparent background)
- Aspect ratio will be preserved
- Images will be scaled to fit within 180x140 pixels bounding box
- Recommended image size: at least 360x280 pixels for good quality

PLACEHOLDER BEHAVIOR
--------------------
If images are missing for a bundle, the experiment will automatically
generate gray placeholder boxes with product names.


