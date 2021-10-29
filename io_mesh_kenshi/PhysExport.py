#!BPY

"""
Name: 'OGRE for Kenshi (*.MESH)'
Blender: 2.8+
Group: 'Import/Export'
Tooltip: 'Import/Export Kenshi OGRE mesh files'

Author: someone, Kindrad

Based on the Torchlight Impost/Export script by 'Dusho'

Also thanks to'goatman' for his port of Ogre export script from 2.49b to 2.5x,
and 'CCCenturion' for trying to refactor the code to be nicer (to be included)

last edited by Kindrad Oct-29-2021

"""

__author__ = "someone, Kindrad"
__version__ = "2.9.1 29-Oct-2021"

__bpydoc__ = """\
This script imports/exports Kenshi Ogre models into/from Blender.

History:<br>
    * v0.4   (07-May-2019) - Switched to Blender 2.80 API
    * v0.3   (08-Mar-2018) - Fixed capsule orientation
    * v0.2   (06-Nov-2017) - Convex mesh calculated for export
    * v0.1   (13-Oct-2017) - Export of box,sphere,capsule,mesh,convex hull from blender physics data
"""

#from Blender import *
from xml.dom import minidom
import bpy
from mathutils import Vector, Matrix
import math
import os
import subprocess
import shutil

def shapeBounds(obj):
    x = obj.bound_box[6][0] - obj.bound_box[0][0]
    y = obj.bound_box[6][1] - obj.bound_box[0][1]
    z = obj.bound_box[6][2] - obj.bound_box[0][2]
    return (x, y, z)

def removeScaleFromMatrix(m):
    print(m)
    loc, rot, sca = m.decompose()
    print("loc:", loc)
    m =  Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
    print(m)
    return (m, sca)

## ------------------------------------------------------------------------------------------------------------------------------------- ##
def exportMeshData(xDoc, mesh, transform):

    triangles = []
    mesh.calc_loop_triangles()
    for tri in mesh.loop_triangles:
        triangles.extend( tri.vertices )
    
    vertices = []
    for vx in mesh.vertices:
        v = transform @ vx.co
        vertices.append( ' '.join(map(str, v)))
    
    xPoints    = xDoc.createElement('points')
    xTriangles = xDoc.createElement('triangles')
    xTriangles.appendChild( xDoc.createTextNode( ' '.join(map(str,triangles)) ))
    xPoints.appendChild( xDoc.createTextNode( ' '.join(map(str,vertices)) ))
    return xPoints, xTriangles


## ------------------------------------------------------------------------------------------------------------------------------------- ##
def saveBoxCollision(xDoc, xCollection, xActor, obj, transform):
    mat, scale = removeScaleFromMatrix(transform @ obj.matrix_world)
    saveTransform(xDoc, xActor, 'globalPose', mat)
    bounds = shapeBounds(obj)
    print('bounds: ', bounds, ' scale: ', scale)
    xShape = xDoc.createElement('NxBoxShapeDesc')
    xShape.setAttribute('dimensions', '{0:f} {1:f} {2:f}'.format( bounds[0] * scale[0] * 0.5, bounds[1] * scale[1] * 0.5, bounds[2] * scale[2] * 0.5 ))
    xActor.appendChild(xShape)
## ------------------------------------------------------------------------------------------------------------------------------------- ##
def saveCapsuleCollision(xDoc, xCollection, xActor, obj, transform):
    fix = Matrix( [ (1,0,0,0),(0,0,1,0),(0,1,0,0),(0,0,0,1) ] )
    mat, scale = removeScaleFromMatrix(transform @ obj.matrix_world * fix )
    saveTransform(xDoc, xActor, 'globalPose', mat)
    bounds = shapeBounds(obj)
    radius = 0.5 * max( abs(bounds[0] * scale[0]), abs(bounds[1] * scale[1]))
    xShape = xDoc.createElement('NxCapsuleShapeDesc')
    xShape.setAttribute('radius', '%6f' % radius)
    xShape.setAttribute('height', '%6f' % (abs(bounds[2]*scale[2]) - 2*radius) )
    xActor.appendChild(xShape)
## ------------------------------------------------------------------------------------------------------------------------------------- ##
def saveSphereCollision(xDoc, xCollection, xActor, obj, transform):
    mat, scale = removeScaleFromMatrix(transform @ obj.matrix_world)
    saveTransform(xDoc, xActor, 'globalPose', mat)
    bounds = shapeBounds(obj)
    xShape = xDoc.createElement('NxSphereShapeDesc')
    xShape.setAttribute('radius', str(max(bounds) * max(scale))) # probaly wrong
    xActor.appendChild(xShape)
## ------------------------------------------------------------------------------------------------------------------------------------- ##
def saveConvexCollision(xDoc, xCollection, xActor, obj, transform):
    mat, scale = removeScaleFromMatrix(transform @ obj.matrix_world )
    scaleMatrix = Matrix([(scale[0],0,0,0),(0,scale[1],0,0),(0,0,scale[2],0),(0,0,0,1)])
    
    # Create convex mesh copy
    apply_modifiers = obj.rigid_body.mesh_source == 'FINAL'
    mesh = obj.to_mesh(apply_modifiers)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    r = bmesh.ops.convex_hull(bm, input=bm.verts)
    #bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    del bm
    
    # Save mesh
    xPoints, xTriangles = exportMeshData(xDoc, mesh, scaleMatrix)
    xMesh = xDoc.createElement('NxConvexMeshDesc')
    xMesh.setAttribute('id', obj.name)
    xMesh.appendChild(xPoints)
    xMesh.appendChild(xTriangles)
    xCollection.appendChild(xMesh)
    # Save shape
    saveTransform(xDoc, xActor, 'globalPose', mat)
    xShape = xDoc.createElement('NxConvexShapeDesc')
    xShape.setAttribute('meshData', obj.name)
    xActor.appendChild(xShape)

## ------------------------------------------------------------------------------------------------------------------------------------- ##
def saveMeshCollision(xDoc, xCollection, xActor, obj, transform):
    mesh = obj.data if not obj.rigid_body.mesh_source == 'FINAL' else obj.to_mesh(True)
    xPoints, xTriangles = exportMeshData(xDoc, mesh, transform @ obj.matrix_world)
    xMesh      = xDoc.createElement('NxTriangleMeshDesc')
    xMeshData  = xDoc.createElement('NxSimpleTriangleMesh')
    xMesh.appendChild(xMeshData)
    xMeshData.appendChild(xPoints)
    xMeshData.appendChild(xTriangles)
    xMesh.setAttribute('id', obj.name)
    xCollection.appendChild(xMesh)
    
    # Add shape
    xShape = xDoc.createElement('NxTriangleMeshShapeDesc')
    xShape.setAttribute('meshData', obj.name)
    xActor.appendChild(xShape)

## ------------------------------------------------------------------------------------------------------------------------------------- ##
def saveTransform(xDoc, xObject, name, m):
    mat = '{0:f} {1:f} {2:f}  {3:f} {4:f} {5:f}  {6:f} {7:f} {8:f}  {9:f} {10:f} {11:f}'.format(m[0][0], m[0][1], m[0][2], m[1][0], m[1][1], m[1][2], m[2][0], m[2][1], m[2][2], m[0][3], m[1][3], m[2][3])
    xTransform = xDoc.createElement(name)
    xText = xDoc.createTextNode( mat )
    xObject.appendChild(xTransform)
    xTransform.appendChild(xText)

def hasCollision(operator, object, types):
    if not object.rigid_body: return False
    if object.rigid_body.collision_shape in types: return True
    operator.report( {'WARNING'}, "Unsupported collision shape : " + object.rigid_body.collision_shape)
    return False

def addChildrenToSet(operator, object, set, types):
    for child in object.children:
        if hasCollision(operator, child, types):
            set.add(child)
        addChildrenToSet(operator, child, set, types)

def commonParent(a, b):
    if not a or not b: return None
    # depth in tree
    da = 0
    db = 0
    p = a
    while p:
        da += 1
        p = p.parent
    p = b
    while p:
        db += 1
        p = p.parent
    
    while da > db:
        da -= 1
        a = a.parent
    while db > da:
        db -= 1
        b = b.parent
    
    while a != b:
        a = a.parent
        b = b.parent
    
    return a


def save(operator, context, filepath,
         objects=0,		# How to specify this?
         transform=0,		# All, Selected, Selected+Children
         dynamicObjects=False
         ):

    # just check if there is extension - .xml
    if '.xml' not in filepath.lower():
        filepath = filepath + ".xml"
    print("Saving", str(filepath))
    
    # go to the object mode
    for ob in bpy.data.objects:
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # List of supported collision types
    shapeFunctions = { 'BOX': saveBoxCollision,
                       'SPHERE': saveSphereCollision, 
                       'CAPSULE': saveCapsuleCollision,
                       'CONVEX_HULL': saveConvexCollision,
                       'MESH': saveMeshCollision }
    
    # get objects to export
    bodies = None
    if objects == 'ALL':
        bodies = []
        for ob in context.scene.objects:
            if hasCollision(operator, ob, shapeFunctions.keys()):
                bodies.append(ob)
    elif objects == 'SELECTED':
        bodies = []
        for ob in context.scene.objects:
            if ob.select_get() and hasCollision(operator, ob, shapeFunctions.keys()):
                bodies.append(ob)
    elif objects == 'CHILDREN':
        bodies = set()
        for ob in context.scene.objects:
            if ob.select_set(True):
                if hasCollision(operator, ob, shapeFunctions.keys()): bodies.add(ob)
                addChildrenToSet(operator, ob, bodies, shapeFunctions.keys())

    # Nothing to export
    if len(bodies)==0:
        print("No collision to export.")
        operator.report( {'WARNING'}, "No collision selected for export")
        return {'CANCELLED'}
    
    # Calculate root transform
    root = Matrix()
    if transform == 'ACTIVE':
        root = bpy.context.scene.objects.active.matrix_world.inverted()
    elif transform == 'PARENT':
        # Locate common parent
        parent = None
        for o in bodies:
            if not parent: parent = o.parent
            else: parent = commonParent(parent, o)
            if not parent: break
        if parent:
            root = parent.matrix_world.inverted()

    # Write xml
    from xml.dom.minidom import Document
    xDoc = Document()
    xRoot = xDoc.createElement('NXUSTREAM2')
    xScene = xDoc.createElement('NxSceneDesc')
    xMaterial = xDoc.createElement('NxMaterialDesc')
    xCollection = xDoc.createElement('NxuPhysicsCollection')
    xCollection.setAttribute('id', filepath)
    xCollection.setAttribute('sdkVersion', '284')
    xCollection.setAttribute('nxuVersion', '103')
    xScene.setAttribute('id', 'collision')
    xScene.setAttribute('hasMaxBounds', 'false')
    xScene.setAttribute('hasLimits', 'false')
    xScene.setAttribute('hasFilter', 'false')
    xMaterial.setAttribute('id', 'Material')
    xMaterial.setAttribute('materialIndex', '0')
    xDoc.appendChild(xRoot)
    xRoot.appendChild(xCollection)
    xCollection.appendChild(xScene)
    
    # Actors
    for body in bodies:
        xActor= xDoc.createElement('NxActorDesc')
        xActor.setAttribute('id', 'name')
        xActor.setAttribute('name', body.name)
        xActor.setAttribute('hasBody', 'false')
        saveShape = shapeFunctions[body.rigid_body.collision_shape]
        saveShape(xDoc, xCollection, xActor, body, root)
        xScene.appendChild(xActor)
    
    # Write xml file
    data = xDoc.toprettyxml(indent='    ')
    f = open( filepath, 'wb' )
    f.write( bytes(data,'utf-8') )
    f.close()
    
    print("done.")
    return {'FINISHED'}

