# Kenshi_IO_Continued
A continuation of the Kenshi IO plugin. Has some bugs fixes and new features...

### How to Install:
Simple:

Download as zip and add the "io_mesh_kenshi" folder to your blender addons folder.

or

With Github:

Clone locally and add a symlink from your blender addon folder to the "io_mesh_kenshi" folder so it works from locally cloned folder instead. This will let you update more easily.

### New Features:
+ Works on latest Blender 3.1+
+ Adding "H_" to the name of a bone prevents it from being exported, use this if you want helper bones (ie: IK targets) in the skeleton.
+ Added ability to import multiple files at once. To facilitate this imported objects are named after the filename as opposed to material name (which was usually 'default')
+ Added a Batch export option. When exporting multiple meshes you can optionally batch export them, they will be named according to the object name in Blender.

### Bugfixes compared to original:
+ Fixes bug when exporting multiple animations at once, animations no longer stack last frame of previous animation.
+ Fixed issue with bone constraints, drivers, etc not being applied to animations on export.
+ Fixed bug related to certain meshes failing to import vertex colors.
+ I'm sure there are others and I can't remember what they were...

### Known outstanding issues:
+ There are a lot of bugs related to the exporting of Physx objects. Currently I have no intentions of fixing these as I've made a set of Unity scripts to do this instead.
