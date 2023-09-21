# Turntable Render Addon for Blender

## Overview

This Blender addon was developed for use at Hallway to facilitate the production of masks that can be passed into stable diffusion processes. It provides a streamlined way to generate turntable renders, capturing even segments around a 360-degree rotation of your object.

## Features

- **Even Segmentation**: Automatically calculates even segments for a 360-degree turntable render.
- **Render Layer Pass Control**: Enables and disables render layer passes based on your selection, including options for Combined, Depth, Normal, and Alpha passes.
- **Automatic Compositor Setup**: Sets up the compositor nodes required for the selected render layer passes, ensuring that your render outputs are correctly processed.
- **Settings Restoration**: After rendering, the addon restores any compositor and render settings you were previously using, ensuring a non-disruptive workflow.

## Installation

1. Download the addon from the GitHub repository.
2. Open Blender and go to `Edit > Preferences > Add-ons`.
3. Click `Install` and navigate to the downloaded addon file to install it.
4. Enable the addon by checking the box next to its name.

## Usage

1. Open the addon panel located in `View3D > UI > Tools`.
2. Configure your settings, such as the number of images, render pass, and output directory.
3. Click the `Render Turntable` button to start the rendering process.

## Contributing

Feel free to open issues or submit pull requests to improve the addon.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

For more information, please visit our [GitHub repository](#).
