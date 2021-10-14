# Kenshi_IO_Continued
A continuation of the Kenshi IO plugin. Has some bugs fixes and new features...


New Features:
+ Adding "H_" to the name of a bone prevents it from being exported, use this if you want helper bones (ie: IK targets) in the skeleton.
+ Added a Batch export option. When exporting multiple meshes you can optionally batch export them, they will be named according to the object name in Blender.

Bugfixes:
+ Fixes bug when exporting multiple animations at once, animations no longer stack last frame of previous animation.
+ I'm sure there are others and I can't remember what they were...
