# Kenshi_IO_Continued
A fork of the Official Kenshi Blender IO addon. This fork has new features, numerous bugfixes, and quality of life changes. This addon also supports Blender 3.0 and foward if newer Blender features are desired.

# New Features:
+ Works on Blender 3.0+. It should work as far back as 2.8 though
+ Meshes with skeleton can be exported to Scythe. (Thank you @boasz for figuring this out)
+ Adding "H_" to the name of a bone prevents it from being exported, use this if you want helper bones (ie: IK targets) in the skeleton.
+ Added ability to import multiple files at once. To facilitate this imported objects are named after the filename as opposed to material name (which was usually 'default')
+ Added a Batch export option. When exporting multiple meshes you can optionally batch export them, they will be named according to the object name in Blender.
+ Added support for exporting alpha from main vertex color. (The older "alpha" secondary vertex color set still works)

# Bugfixes compared to original:
+ Fixes bug when exporting multiple animations at once, animations no longer stack last frame of previous animation.
+ Fixed issue with bone constraints, drivers, etc not being applied to animations on export.
+ Fixed bug related to certain meshes failing to import vertex colors.
+ Fixes numerous crashes and bugs when using Blender versions 2.9 and later.
+ Fixes mesh collider export
+ I'm sure there are others and I can't remember what they were...

# Known outstanding issues:
+ There are still some bugs related to the export of colliders. Box and (non-convex) Mesh Colliders should work (these are the most important). Sphere, Capsule, and Convex Mesh Colliders are still problematic. As Box and Mesh are more important fixing these is low priority.

# How to Install:

## DO NOT USE THE ADDON INSTALL FUNCTION THROUGH BLENDER, MANUALLY INSTALL INSTEAD USING INSTRUCTIONS BELOW

### Simple Install:

1. Download.
<img src="https://github.com/Kindrad/Kenshi_IO_Continued/blob/main/install_instructions/Step_1.png" height="200"/>

2. Add the "io_mesh_kenshi_continued" from the zip folder to your Blender addons folder.
The folder structure should look like this: "C:\Users[username]\AppData\Roaming\Blender Foundation\Blender\3.X\scripts\addons\io_mesh_kenshi_continued" 
<img src="https://github.com/Kindrad/Kenshi_IO_Continued/blob/main/install_instructions/Step_2.png" height="200"/>

3. Enable addon in the Blender addons.
<img src="https://github.com/Kindrad/Kenshi_IO_Continued/blob/main/install_instructions/Step_3a.png" height="200"/>
<img src="https://github.com/Kindrad/Kenshi_IO_Continued/blob/main/install_instructions/Step_3b.png" height="200"/>

### or

### With Github:

This will update the addon regularly. I assume you probably don't need pictures if you are doing this.

1. Clone locally
2. Add a symlink from your Blender addon folder to the "io_mesh_kenshi_continued" folder at your local git location.
The symlink file structure should look like this: "C:\Users[username]\AppData\Roaming\Blender Foundation\Blender\3.X\scripts\addons\io_mesh_kenshi_continued"
3. Enable addon in the Blender addons.

