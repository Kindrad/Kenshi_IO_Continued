# Kenshi_IO_Continued
A continuation of the Kenshi IO plugin. Has some bugs fixes and new features...

### How to Install:
Simple:

Download as zip and add the "io_mesh_kenshi" folder to your blender addons folder.

or

With Github:

Clone locally and add a symlink from your blender addon folder to the "io_mesh_kenshi" folder so it works from locally cloned folder instead. This will let you update more easily.

### New Features:
+ Works on latest Blender 2.9+
+ Adding "H_" to the name of a bone prevents it from being exported, use this if you want helper bones (ie: IK targets) in the skeleton.
+ Added a Batch export option. When exporting multiple meshes you can optionally batch export them, they will be named according to the object name in Blender.

### Bugfixes:
+ Fixes bug when exporting multiple animations at once, animations no longer stack last frame of previous animation.
+ Fixed issue with bone constraints, drivers, etc not being applied to animations on export.
+ I'm sure there are others and I can't remember what they were...
