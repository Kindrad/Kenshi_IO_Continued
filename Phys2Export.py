#!BPY

"""
Blender: 2.80
Author: Someone
History:<br>
    * v0.1   (28-May-2019) - Export of box,sphere,capsule,mesh,convex hull from blender physics data for physx 3.4.0
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

def appendTextNode(parent, name, text):
    node = parent.ownerDocument.createElement(name)
    node.appendChild( parent.ownerDocument.createTextNode( text ))
    parent.appendChild(node)
    return node

## ------------------------------------------------------------------------------------------------------------------------------------- ##
def formatMeshData(mesh, transform, tris):
    vertices = []
    for vx in mesh.vertices:
        v = transform @ vx.co
        vertices.append( ' '.join(map(str, v)))
    
    triangles = []
    if tris:
        mesh.calc_loop_triangles()
        for tri in mesh.loop_triangles:
            triangles.extend( tri.vertices )
    
    return (' '.join(map(str,vertices)), ' '.join(map(str,triangles)))

## ------------------------------------------------------------------------------------------------------------------------------------- ##
def createShape(xShapes, name, transform):
    xShape = xShapes.ownerDocument.createElement('PxShape')
    saveTransform(xShape, 'LocalPose', transform)
    appendTextNode(xShape, 'SimulationFilterData', '65537')
    appendTextNode(xShape, 'ContactOffset',        '1')
    appendTextNode(xShape, 'RestOffset',           '0')
    appendTextNode(xShape, 'Flags',                'eSIMULATION_SHAPE|eSCENE_QUERY_SHAPE|eVISUALIZATION')
    appendTextNode(xShape, 'Name',                 name)
    
    xMaterial = xShape.appendChild( xShapes.ownerDocument.createElement('Materials') )
    appendTextNode(xMaterial, 'PxMaterialRef', '1893755024') # global constant
    
    xShapes.appendChild(xShape)
    return xShape


## ------------------------------------------------------------------------------------------------------------------------------------- ##
def saveBoxCollision(xRoot, xShapes, obj, transform):
    mat, scale = removeScaleFromMatrix(transform @ obj.matrix_world)
    xShape = createShape(xShapes, obj.name, mat)
    
    bounds = shapeBounds(obj)
    print('bounds: ', bounds, ' scale: ', scale)
    
    xGeom = xShape.ownerDocument.createElement('Geometry')
    xBox = xShape.ownerDocument.createElement('PxBoxGeometry')
    appendTextNode(xBox, 'HalfExtents', '{0:f} {1:f} {2:f}'.format( bounds[0] * scale[0] * 0.5, bounds[1] * scale[1] * 0.5, bounds[2] * scale[2] * 0.5 ))
    xShape.appendChild(xGeom)
    xGeom.appendChild(xBox)

## ------------------------------------------------------------------------------------------------------------------------------------- ##
def saveCapsuleCollision(xRoot, xShapes, obj, transform):
    fix = Matrix( [ (0,0,1,0),(0,1,0,0),(-1,0,0,0),(0,0,0,1) ] ) # Rotation fix as blender capsules are in Z axis whereas physx uses X axis
    mat, scale = removeScaleFromMatrix(transform @ obj.matrix_world @ fix )
    xShape = createShape(xShapes, obj.name, mat)
    bounds = shapeBounds(obj)
    radius = 0.5 * max( abs(bounds[0] * scale[0]), abs(bounds[1] * scale[1]))
    height = abs(bounds[2]*scale[2]) - 2 * radius
    
    print('bounds: ', bounds, 'scale', scale, ' radius: ', radius, 'height', height)
    
    xGeom = xShape.ownerDocument.createElement('Geometry')
    xCapsule = xShape.ownerDocument.createElement('PxCapsuleGeometry')
    appendTextNode(xCapsule, 'Radius', str(radius))
    appendTextNode(xCapsule, 'HalfHeight', str(height * 0.5))
    xShape.appendChild(xGeom)
    xGeom.appendChild(xCapsule)

## ------------------------------------------------------------------------------------------------------------------------------------- ##
def saveSphereCollision(xRoot, xShapes, obj, transform):
    mat, scale = removeScaleFromMatrix(transform @ obj.matrix_world)
    xShape = createShape(xShapes, obj.name, mat)
    bounds = shapeBounds(obj)
    
    xGeom = xShape.ownerDocument.createElement('Geometry')
    xSphere = xShape.ownerDocument.createElement('PxSphereGeometry')
    appendTextNode(xSphere, 'Radius', str(max(bounds) * max(scale)))
    xShape.appendChild(xGeom)
    xGeom.appendChild(xSphere)

## ------------------------------------------------------------------------------------------------------------------------------------- ##
def saveConvexCollision(xRoot, xShapes, obj, transform):
    mat, scale = removeScaleFromMatrix(transform @ obj.matrix_world )
    scaleMatrix = Matrix([(scale[0],0,0,0),(0,scale[1],0,0),(0,0,scale[2],0),(0,0,0,1)])
    
    # Create convex mesh copy
    apply_modifiers = obj.rigid_body.mesh_source == 'FINAL'
    depsgraph = bpy.context.evaluated_depsgraph_get()
    tobj = obj.evaluated_get(depsgraph) if apply_modifiers else obj
    mesh = tobj.to_mesh()
    
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    r = bmesh.ops.convex_hull(bm, input=bm.verts)
    #bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    del bm
    
    # Save mesh
    xDoc = xShapes.ownerDocument
    points, triangles = formatMeshData(mesh, scaleMatrix, False)
    id = str(hash(points)&0xefffffff)
    xMesh = xDoc.createElement('PxConvexMesh')
    appendTextNode(xMesh, 'Id', id)
    appendTextNode(xMesh, 'Points', points)
    xRoot.insertBefore(xMesh, xRoot.firstChild)
    
    # Save shape
    xShape = createShape(xShapes, obj.name, mat)
    xGeom = xShape.appendChild( xDoc.createElement('Geometry') )
    xMesh = xGeom.appendChild( xDoc.createElement('PxConvexMeshGeometry') )
    xScale = xMesh.appendChild( xDoc.createElement('Scale') )
    appendTextNode(xScale, 'Scale', '1 1 1')
    appendTextNode(xScale, 'Rotation', '0 0 0 1')
    appendTextNode(xMesh, 'ConvexMesh', id)
    
    tobj.to_mesh_clear()

## ------------------------------------------------------------------------------------------------------------------------------------- ##
def saveMeshCollision(xRoot, xShapes, obj, transform):
    # Get mesh
    apply_modifiers = obj.rigid_body.mesh_source == 'FINAL'
    depsgraph = bpy.context.evaluated_depsgraph_get()
    tobj = obj.evaluated_get(depsgraph) if apply_modifiers else obj
    mesh = tobj.to_mesh()
 
    # Save mesh
    xDoc = xShapes.ownerDocument
    points, triangles = formatMeshData(mesh, transform @ obj.matrix_world, True)
    id = str(hash(points)&0xefffffff)
    xMesh = xDoc.createElement('PxBVH33TriangleMesh')
    appendTextNode(xMesh, 'Id', id)
    appendTextNode(xMesh, 'Points', points)
    appendTextNode(xMesh, 'Triangles', triangles)
    xRoot.insertBefore(xMesh, xRoot.firstChild)
    
    # Save shape
    xShape = createShape(xShapes, obj.name, Matrix())
    xGeom = xShape.appendChild( xDoc.createElement('Geometry') )
    xMesh = xGeom.appendChild( xDoc.createElement('PxTriangleMeshGeometry') )
    xScale = xMesh.appendChild( xDoc.createElement('Scale') )
    appendTextNode(xScale, 'Scale', '1 1 1')
    appendTextNode(xScale, 'Rotation', '0 0 0 1')
    appendTextNode(xMesh, 'TriangleMesh', id)
    
    tobj.to_mesh_clear()


## ------------------------------------------------------------------------------------------------------------------------------------- ##
def saveTransform(xObject, name, m):
    q = m.to_quaternion()
    p = m.to_translation()
    print(name, q, p)
    trans = '{0:f} {1:f} {2:f} {3:f}  {4:f} {5:f} {6:f}'.format(q[1], q[2], q[3], q[0], p[0], p[1], p[2])
    appendTextNode(xObject, name, trans)

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
    
    return a;


def save(operator, context, filepath,
         objects=0,		# How to specify this?
         transform=0,		# All, Selected, Selected+Children
         dynamicObjects=False
         ):

    # just check if there is extension - .xml
    if '.repx' not in filepath.lower():
        filepath = filepath + ".repx"
    print("Saving", str(filepath))
    
    # go to the object mode
    if context.active_object:
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # List of supported collision types
    shapeFunctions = { 'BOX':         saveBoxCollision,
                       'SPHERE':      saveSphereCollision, 
                       'CAPSULE':     saveCapsuleCollision,
                       'CONVEX_HULL': saveConvexCollision,
                       'MESH':        saveMeshCollision }
    
    # get objects to export
    bodies = None
    if objects == 'ALL':
        bodies = []
        for ob in context.view_layer.objects:
            if hasCollision(operator, ob, shapeFunctions.keys()):
                bodies.append(ob)
    elif objects == 'SELECTED':
        bodies = []
        for ob in context.view_layer.objects:
            if ob.select_get() and hasCollision(operator, ob, shapeFunctions.keys()):
                bodies.append(ob)
    elif objects == 'CHILDREN':
        bodies = set()
        for ob in context.view_layer.objects:
            if ob.select_get():
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
    xRoot = xDoc.createElement('PhysX30Collection')
    xRoot.setAttribute('version', '3.4.0')
    
    # Material
    materialID = '1893755024'
    xMaterial = xDoc.createElement('PxMaterial')
    appendTextNode(xMaterial, 'Id',              materialID)
    appendTextNode(xMaterial, 'DynamicFriction', '0.3')
    appendTextNode(xMaterial, 'StaticFriction',  '0.3')
    appendTextNode(xMaterial, 'Restitution',     '0.5')
    appendTextNode(xMaterial, 'FrictionCombineMode',    'eAVERAGE')
    appendTextNode(xMaterial, 'RestitutionCombineMode', 'eAVERAGE')
    
    xDoc.appendChild(xRoot)
    xRoot.appendChild(xMaterial)
    
    r = filepath.rfind('/') + 1
    if r == 0: r = filepath.rfind('\\') + 1
    title = filepath[r:]
    
    # All shapes in a single actor? Make this an option. Also be good to use: body.rigid_body.type == { 'ACTIVE', 'PASSIVE' }
    # and perhaps some material properties from the rigid boty rather than hard coded here
    xActor= xDoc.createElement('PxRigidDynamic' if dynamicObjects else 'PxRigidStatic')
    appendTextNode(xActor, 'Id', str(hash(title)&0xefffffff))
    appendTextNode(xActor, 'Name', title)
    appendTextNode(xActor, 'ActorFlags', 'eVISUALIZATION')
    appendTextNode(xActor, 'GlobalPose', '0 0 0 1 0 0 0')   # I assume this is quaternion.xyzw position.xyz
    xShapes = xDoc.createElement('Shapes')
    
    xRoot.appendChild(xActor)
    xActor.appendChild(xShapes)
    
    for body in bodies:
        saveShape = shapeFunctions[ body.rigid_body.collision_shape ]
        saveShape(xRoot, xShapes, body, root)
    
    # Write xml file
    data = xDoc.toprettyxml(indent='    ')
    f = open( filepath, 'wb' )
    f.write( bytes(data,'utf-8') )
    f.close()
    
    print("done.")
    return {'FINISHED'}

