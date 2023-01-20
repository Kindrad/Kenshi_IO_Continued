# Kenshi_IO_Continued
A continuation of the Kenshi IO plugin. Has some bugs fixes and new features...

# How to Install:

## DO NOT USE THE ADDON INSTALL FUNCTION THROUGH BLENDER, MANUALLY INSTALL INSTEAD USING INSTRUCTIONS BELOW

### Simple:

Download as zip and add the "io_mesh_kenshi_continued" folder to your blender addons folder.

The folder structure should look like this: "C:\Users[username]\AppData\Roaming\Blender Foundation\Blender\3.X\scripts\addons\io_mesh_kenshi_continued"

#### or

### With Github:

Clone locally and add a symlink from your blender addon folder to the "io_mesh_kenshi_continued" folder so it works from locally cloned folder instead. This will let you update more easily.


The folder structure should look like this: "C:\Users[username]\AppData\Roaming\Blender Foundation\Blender\3.X\scripts\addons\io_mesh_kenshi_continued"


# New Features:
+ Works on Blender 3.0+. It should work as far back as 2.8 though
+ Meshes with skeleton can be exported to Scythe. (Thank you @boasz for figuring this out)
+ Adding "H_" to the name of a bone prevents it from being exported, use this if you want helper bones (ie: IK targets) in the skeleton.
+ Added ability to import multiple files at once. To facilitate this imported objects are named after the filename as opposed to material name (which was usually 'default')
+ Added a Batch export option. When exporting multiple meshes you can optionally batch export them, they will be named according to the object name in Blender.
+ Added support for exporting alpha from main vertex color. (The older "alpha" secondary vertex color set still works)

# Bugfixes compared to original:
+ Fixed mesh collider export
+ Fixes bug when exporting multiple animations at once, animations no longer stack last frame of previous animation.
+ Fixed issue with bone constraints, drivers, etc not being applied to animations on export.
+ Fixed bug related to certain meshes failing to import vertex colors.
+ Fixed fatal crash when importing .mesh files into Blender 3.2
+ I'm sure there are others and I can't remember what they were...

# Known outstanding issues:
+ There are still some bugs related to the export of colliders. Box and (non-convex) Mesh Colliders should work (these are the most important). Sphere, Capsule, and Convex Mesh Colliders are still problematic. As Box and Mesh are more important fixing these is low priority.
